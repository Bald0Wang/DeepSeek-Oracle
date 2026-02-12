from __future__ import annotations

import json
import queue
import threading

from flask import Blueprint, Response, current_app, request, stream_with_context

from app.schemas import validate_oracle_chat_payload
from app.services import get_oracle_orchestrator_service
from app.utils.auth import require_auth
from app.utils.response import success_response


oracle_bp = Blueprint("oracle", __name__)


@oracle_bp.post("/oracle/chat")
@require_auth()
def oracle_chat():
    payload = request.get_json(silent=True) or {}
    normalized = validate_oracle_chat_payload(payload)

    data = get_oracle_orchestrator_service().chat(normalized)
    return success_response(data=data)


@oracle_bp.post("/oracle/chat/stream")
@require_auth()
def oracle_chat_stream():
    payload = request.get_json(silent=True) or {}
    normalized = validate_oracle_chat_payload(payload)
    event_queue: queue.Queue[tuple[str, dict]] = queue.Queue()
    app = current_app._get_current_object()

    def push_event(event_name: str, event_data: dict) -> None:
        event_queue.put((event_name, event_data))

    def run_chat() -> None:
        try:
            with app.app_context():
                get_oracle_orchestrator_service().chat_stream(normalized, event_callback=push_event)
        except Exception as exc:  # pragma: no cover - stream guard
            push_event("error", {"message": str(exc)})
        finally:
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
