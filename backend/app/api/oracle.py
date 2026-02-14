from __future__ import annotations

import json
import queue
import threading

from flask import Blueprint, Response, current_app, g, request, stream_with_context

from app.models import OracleChatRepo
from app.schemas import validate_oracle_chat_payload
from app.services import get_oracle_orchestrator_service
from app.utils.errors import business_error
from app.utils.auth import require_auth, resolve_request_user
from app.utils.response import success_response


oracle_bp = Blueprint("oracle", __name__)


def _get_oracle_chat_repo() -> OracleChatRepo:
    return OracleChatRepo(current_app.config["DATABASE_PATH"])


def _get_current_user_id() -> int:
    current_user = getattr(g, "current_user", None) or {}
    return int(current_user.get("id", 0))


def _build_conversation_title(user_query: str) -> str:
    compact = " ".join((user_query or "").split())
    return compact[:26] if compact else "新对话"


def _resolve_conversation_id(repo: OracleChatRepo, user_id: int, normalized: dict) -> int:
    conversation_id = normalized.get("conversation_id")
    if conversation_id is None:
        created = repo.create_conversation(
            user_id=user_id,
            title=_build_conversation_title(str(normalized.get("user_query", ""))),
        )
        return int(created["id"])

    conversation = repo.get_conversation(user_id=user_id, conversation_id=int(conversation_id))
    if not conversation:
        raise business_error("A4042", "conversation not found", 404, False)
    return int(conversation["id"])


def _persist_turn(
    repo: OracleChatRepo,
    conversation_id: int,
    normalized: dict,
    result: dict | None = None,
    error_message: str | None = None,
) -> None:
    payload = result or {}
    status = "failed" if error_message else "succeeded"
    repo.append_turn(
        conversation_id=conversation_id,
        user_query=str(normalized.get("user_query", "")).strip(),
        context_summary=str(normalized.get("conversation_history_summary", "")).strip(),
        status=status,
        plan_steps=list(payload.get("tool_events") or []),
        answer_text="" if error_message else str(payload.get("answer_text", "")),
        action_items=list(payload.get("action_items") or []),
        follow_up_questions=list(payload.get("follow_up_questions") or []),
        safety_disclaimer_level=str(payload.get("safety_disclaimer_level", "none")),
        error_message=error_message,
    )


@oracle_bp.post("/oracle/chat")
def oracle_chat():
    resolve_request_user(optional=True)
    user_id = _get_current_user_id()
    payload = request.get_json(silent=True) or {}
    normalized = validate_oracle_chat_payload(payload)
    if user_id <= 0:
        normalized.pop("conversation_id", None)
        data = get_oracle_orchestrator_service().chat(normalized)
        return success_response(data=data)

    repo = _get_oracle_chat_repo()
    conversation_id = _resolve_conversation_id(repo=repo, user_id=user_id, normalized=normalized)
    normalized["conversation_id"] = conversation_id

    data = get_oracle_orchestrator_service().chat(normalized)
    _persist_turn(repo=repo, conversation_id=conversation_id, normalized=normalized, result=data)
    data["conversation_id"] = conversation_id
    return success_response(data=data)


@oracle_bp.post("/oracle/conversations")
@require_auth()
def create_oracle_conversation():
    user_id = _get_current_user_id()
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip() or "新对话"
    data = _get_oracle_chat_repo().create_conversation(user_id=user_id, title=title)
    return success_response(data=data)


@oracle_bp.get("/oracle/conversations")
@require_auth()
def list_oracle_conversations():
    user_id = _get_current_user_id()
    limit_raw = request.args.get("limit", default=50, type=int) or 50
    conversations = _get_oracle_chat_repo().list_conversations(user_id=user_id, limit=limit_raw)
    for item in conversations:
        title = str(item.get("title") or "").strip()
        item["title"] = title or str(item.get("last_query") or "新对话")[:26] or "新对话"
    return success_response(data={"items": conversations})


@oracle_bp.get("/oracle/conversations/<int:conversation_id>/turns")
@require_auth()
def list_oracle_conversation_turns(conversation_id: int):
    user_id = _get_current_user_id()
    repo = _get_oracle_chat_repo()
    conversation = repo.get_conversation(user_id=user_id, conversation_id=conversation_id)
    if not conversation:
        raise business_error("A4042", "conversation not found", 404, False)
    turns = repo.list_turns(user_id=user_id, conversation_id=conversation_id)
    return success_response(data={"conversation": conversation, "turns": turns})


@oracle_bp.post("/oracle/chat/stream")
@require_auth()
def oracle_chat_stream():
    user_id = _get_current_user_id()
    payload = request.get_json(silent=True) or {}
    normalized = validate_oracle_chat_payload(payload)
    repo = _get_oracle_chat_repo()
    conversation_id = _resolve_conversation_id(repo=repo, user_id=user_id, normalized=normalized)
    normalized["conversation_id"] = conversation_id

    event_queue: queue.Queue[tuple[str, dict]] = queue.Queue()
    app = current_app._get_current_object()
    result_holder: dict[str, dict | str] = {}

    def push_event(event_name: str, event_data: dict) -> None:
        if event_name == "final":
            event_data = {**event_data, "conversation_id": conversation_id}
        event_queue.put((event_name, event_data))

    def run_chat() -> None:
        try:
            with app.app_context():
                stream_result = get_oracle_orchestrator_service().chat_stream(normalized, event_callback=push_event)
                stream_result["conversation_id"] = conversation_id
                result_holder["result"] = stream_result
        except Exception as exc:  # pragma: no cover - stream guard
            result_holder["error"] = str(exc)
            push_event("error", {"message": str(exc)})
        finally:
            try:
                with app.app_context():
                    if result_holder.get("result"):
                        _persist_turn(
                            repo=OracleChatRepo(app.config["DATABASE_PATH"]),
                            conversation_id=conversation_id,
                            normalized=normalized,
                            result=result_holder["result"] if isinstance(result_holder["result"], dict) else None,
                        )
                    else:
                        _persist_turn(
                            repo=OracleChatRepo(app.config["DATABASE_PATH"]),
                            conversation_id=conversation_id,
                            normalized=normalized,
                            error_message=str(result_holder.get("error") or "stream failed"),
                        )
            except Exception:  # pragma: no cover - persistence guard
                pass
            push_event("__end__", {})

    def generate():
        worker = threading.Thread(target=run_chat, daemon=True)
        worker.start()
        while True:
            event_name, event_data = event_queue.get()
            if event_name == "__end__":
                break
            payload_text = json.dumps(event_data, ensure_ascii=False)
            yield f"event: {event_name}\n"
            yield f"data: {payload_text}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
