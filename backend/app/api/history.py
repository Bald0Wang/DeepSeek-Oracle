from flask import Blueprint, request

from app.services import get_analysis_service
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
    data = service.get_history(page=page, page_size=page_size)
    return success_response(data=data)


@history_bp.get("/result/<int:result_id>")
@require_auth()
def get_result(result_id: int):
    service = get_analysis_service()
    data = service.get_result(result_id)
    return success_response(data=data)


@history_bp.get("/result/<int:result_id>/<analysis_type>")
@require_auth()
def get_result_item(result_id: int, analysis_type: str):
    service = get_analysis_service()
    data = service.get_result_item(result_id=result_id, analysis_type=analysis_type)
    return success_response(data=data)
