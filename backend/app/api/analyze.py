from flask import Blueprint, g, request

from app.schemas import validate_analyze_payload
from app.services import get_analysis_service
from app.services.llm_settings_service import get_llm_settings_service
from app.utils.auth import require_auth
from app.utils.response import success_response


analyze_bp = Blueprint("analyze", __name__)


@analyze_bp.post("/analyze")
@require_auth()
def submit_analysis():
    payload = request.get_json(silent=True) or {}
    normalized = validate_analyze_payload(payload)
    current_user = getattr(g, "current_user", None) or {}
    user_id = int(current_user.get("id", 0))
    normalized["user_id"] = user_id
    runtime = get_llm_settings_service().resolve_runtime_config(
        user_id=user_id,
        provider_override=normalized.get("provider"),
        model_override=normalized.get("model"),
    )
    normalized["provider"] = runtime["provider"]
    normalized["model"] = runtime["model"]

    service = get_analysis_service()
    result = service.submit_analysis(normalized)

    if result["hit_cache"]:
        return success_response(
            message="cache_hit",
            data={
                "result_id": result["result_id"],
                "hit_cache": True,
            },
            status=200,
        )

    return success_response(
        message="accepted",
        data={
            "task_id": result["task_id"],
            "status": result["status"],
            "poll_after_ms": result["poll_after_ms"],
            "hit_cache": False,
            "reused_task": bool(result.get("reused_task", False)),
        },
        status=202,
    )


@analyze_bp.post("/check_cache")
@require_auth()
def check_cache():
    payload = request.get_json(silent=True) or {}
    normalized = validate_analyze_payload(payload)
    current_user = getattr(g, "current_user", None) or {}
    user_id = int(current_user.get("id", 0))
    normalized["user_id"] = user_id
    runtime = get_llm_settings_service().resolve_runtime_config(
        user_id=user_id,
        provider_override=normalized.get("provider"),
        model_override=normalized.get("model"),
    )
    normalized["provider"] = runtime["provider"]
    normalized["model"] = runtime["model"]

    service = get_analysis_service()
    data = service.check_cache(normalized)
    return success_response(data=data)
