from flask import Blueprint, request

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
