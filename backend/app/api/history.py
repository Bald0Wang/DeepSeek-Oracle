from flask import Blueprint, g, request

from app.services import get_analysis_service, get_divination_service
from app.utils.auth import require_auth
from app.utils.errors import validation_error
from app.utils.response import success_response


history_bp = Blueprint("history", __name__)


@history_bp.get("/history")
@require_auth()
def get_history():
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
    except ValueError as exc:
        raise validation_error("page", "page and page_size must be integer") from exc

    service = get_analysis_service()
    current_user = getattr(g, "current_user", None) or {}
    data = service.get_history(
        page=page,
        page_size=page_size,
        user_id=int(current_user.get("id", 0)),
        is_admin=str(current_user.get("role", "")) == "admin",
    )
    return success_response(data=data)


@history_bp.get("/result/<int:result_id>")
@require_auth()
def get_result(result_id: int):
    service = get_analysis_service()
    current_user = getattr(g, "current_user", None) or {}
    data = service.get_result(
        result_id,
        user_id=int(current_user.get("id", 0)),
        is_admin=str(current_user.get("role", "")) == "admin",
    )
    return success_response(data=data)


@history_bp.get("/result/<int:result_id>/<analysis_type>")
@require_auth()
def get_result_item(result_id: int, analysis_type: str):
    service = get_analysis_service()
    current_user = getattr(g, "current_user", None) or {}
    data = service.get_result_item(
        result_id=result_id,
        analysis_type=analysis_type,
        user_id=int(current_user.get("id", 0)),
        is_admin=str(current_user.get("role", "")) == "admin",
    )
    return success_response(data=data)


@history_bp.get("/history/divinations")
@require_auth()
def get_divination_history():
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
    except ValueError as exc:
        raise validation_error("page", "page and page_size must be integer") from exc

    divination_type = str(request.args.get("type", "")).strip().lower()
    if divination_type not in {"", "all", "ziwei", "meihua"}:
        raise validation_error("type", "type must be all/ziwei/meihua")
    if divination_type == "all":
        divination_type = ""

    current_user = getattr(g, "current_user", None) or {}
    data = get_divination_service().list_records(
        user_id=int(current_user.get("id", 0)),
        page=page,
        page_size=page_size,
        divination_type=divination_type or None,
    )
    return success_response(data=data)


@history_bp.get("/history/divinations/<int:record_id>")
@require_auth()
def get_divination_history_detail(record_id: int):
    current_user = getattr(g, "current_user", None) or {}
    data = get_divination_service().get_record(
        record_id=record_id,
        user_id=int(current_user.get("id", 0)),
        is_admin=str(current_user.get("role", "")) == "admin",
    )
    return success_response(data=data)
