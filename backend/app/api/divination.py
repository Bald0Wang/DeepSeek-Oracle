from flask import Blueprint, g, request

from app.schemas.divination import validate_meihua_divination_payload, validate_ziwei_divination_payload
from app.services import get_divination_service
from app.services.llm_settings_service import get_llm_settings_service
from app.utils.auth import require_auth
from app.utils.response import success_response


divination_bp = Blueprint("divination", __name__)


@divination_bp.post("/divination/ziwei")
@require_auth()
def ziwei_divination():
    payload = request.get_json(silent=True) or {}
    normalized = validate_ziwei_divination_payload(payload)
    current_user = getattr(g, "current_user", None) or {}
    user_id = int(current_user.get("id", 0))
    runtime = get_llm_settings_service().resolve_runtime_config(
        user_id=user_id,
        provider_override=normalized.get("provider"),
        model_override=normalized.get("model"),
    )
    normalized["provider"] = runtime["provider"]
    normalized["model"] = runtime["model"]
    normalized["provider_config"] = runtime["provider_config"]

    service = get_divination_service()
    data = service.run_ziwei(normalized)
    record_id = service.save_ziwei_record(
        user_id=user_id,
        payload=normalized,
        result=data,
    )
    data["record_id"] = record_id
    return success_response(data=data)


@divination_bp.post("/divination/meihua")
@require_auth()
def meihua_divination():
    payload = request.get_json(silent=True) or {}
    normalized = validate_meihua_divination_payload(payload)
    current_user = getattr(g, "current_user", None) or {}
    user_id = int(current_user.get("id", 0))
    runtime = get_llm_settings_service().resolve_runtime_config(
        user_id=user_id,
        provider_override=normalized.get("provider"),
        model_override=normalized.get("model"),
    )
    normalized["provider"] = runtime["provider"]
    normalized["model"] = runtime["model"]
    normalized["provider_config"] = runtime["provider_config"]

    service = get_divination_service()
    data = service.run_meihua(normalized)
    record_id = service.save_meihua_record(
        user_id=user_id,
        payload=normalized,
        result=data,
    )
    data["record_id"] = record_id
    return success_response(data=data)
