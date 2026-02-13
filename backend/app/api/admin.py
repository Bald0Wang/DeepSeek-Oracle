from flask import Blueprint, request

from app.services.admin_service import get_admin_service
from app.utils.auth import require_auth
from app.utils.errors import validation_error
from app.utils.response import success_response


admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/admin/dashboard")
@require_auth(admin_only=True)
def dashboard():
    range_key = str(request.args.get("range", "24h")).strip().lower()
    if range_key not in {"24h", "7d", "30d"}:
        raise validation_error("range", "range must be one of 24h/7d/30d")
    data = get_admin_service().get_dashboard(range_key=range_key)
    return success_response(data=data)


@admin_bp.get("/admin/logs")
@require_auth(admin_only=True)
def logs():
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))
    except ValueError as exc:
        raise validation_error("page", "page and page_size must be integer") from exc

    data = get_admin_service().get_logs(page=page, page_size=page_size)
    return success_response(data=data)


@admin_bp.get("/admin/users")
@require_auth(admin_only=True)
def users():
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
    except ValueError as exc:
        raise validation_error("page", "page and page_size must be integer") from exc

    data = get_admin_service().get_users(page=page, page_size=page_size)
    return success_response(data=data)
