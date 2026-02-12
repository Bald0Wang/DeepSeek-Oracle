from flask import Blueprint, g, request

from app.services import get_insight_service
from app.utils.auth import require_auth
from app.utils.errors import validation_error
from app.utils.response import success_response


insights_bp = Blueprint("insights", __name__)


@insights_bp.get("/insights/overview")
@require_auth()
def get_insight_overview():
    result_id_raw = request.args.get("result_id")
    result_id: int | None = None
    if result_id_raw not in (None, ""):
        try:
            result_id = int(result_id_raw)
        except ValueError as exc:
            raise validation_error("result_id", "result_id must be integer") from exc

    current_user = getattr(g, "current_user", None) or {}
    service = get_insight_service()
    data = service.get_overview(
        user_id=int(current_user.get("id", 0)),
        is_admin=str(current_user.get("role", "")) == "admin",
        result_id=result_id,
    )
    return success_response(data=data)
