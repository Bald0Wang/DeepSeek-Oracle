from flask import Blueprint, request

from app.schemas.divination import validate_meihua_divination_payload, validate_ziwei_divination_payload
from app.services import get_divination_service
from app.utils.auth import require_auth
from app.utils.response import success_response


divination_bp = Blueprint("divination", __name__)


@divination_bp.post("/divination/ziwei")
@require_auth()
def ziwei_divination():
    payload = request.get_json(silent=True) or {}
    normalized = validate_ziwei_divination_payload(payload)
    data = get_divination_service().run_ziwei(normalized)
    return success_response(data=data)


@divination_bp.post("/divination/meihua")
@require_auth()
def meihua_divination():
    payload = request.get_json(silent=True) or {}
    normalized = validate_meihua_divination_payload(payload)
    data = get_divination_service().run_meihua(normalized)
    return success_response(data=data)
