from flask import Blueprint, g, request

from app.schemas import validate_update_llm_settings_payload
from app.services.llm_settings_service import get_llm_settings_service
from app.utils.auth import require_auth
from app.utils.response import success_response


settings_bp = Blueprint("settings", __name__)


def _current_user_id() -> int:
    current_user = getattr(g, "current_user", None) or {}
    return int(current_user.get("id", 0))


@settings_bp.get("/settings/llm")
@require_auth()
def get_llm_settings():
    user_id = _current_user_id()
    data = get_llm_settings_service().get_user_config(user_id)
    return success_response(data=data)


@settings_bp.put("/settings/llm")
@require_auth()
def update_llm_settings():
    user_id = _current_user_id()
    payload = request.get_json(silent=True) or {}
    normalized = validate_update_llm_settings_payload(payload)
    setting = get_llm_settings_service().update_user_config(user_id=user_id, payload=normalized)
    return success_response(message="updated", data={"setting": setting})

