from datetime import datetime

from flask import Blueprint, g, request

from app.services import get_insight_service
from app.utils.auth import require_auth
from app.utils.errors import AppError
from app.utils.errors import validation_error
from app.utils.response import success_response


insights_bp = Blueprint("insights", __name__)


def _validate_birth_info(payload: dict) -> dict:
    raw_birth_info = payload.get("birth_info")
    if not isinstance(raw_birth_info, dict):
        raise validation_error("birth_info", "birth_info is required")

    for field in ["date", "timezone", "gender", "calendar"]:
        if field not in raw_birth_info:
            raise validation_error("birth_info", f"birth_info.{field} is required")

    date_value = str(raw_birth_info.get("date", "")).strip()
    try:
        datetime.strptime(date_value, "%Y-%m-%d")
    except ValueError as exc:
        raise validation_error("birth_info.date", "date must match YYYY-MM-DD") from exc

    try:
        timezone = int(raw_birth_info.get("timezone"))
    except (TypeError, ValueError) as exc:
        raise validation_error("birth_info.timezone", "timezone must be integer") from exc
    if timezone < 0 or timezone > 12:
        raise validation_error("birth_info.timezone", "timezone must be in range 0-12")

    gender = str(raw_birth_info.get("gender", "")).strip()
    if gender not in {"男", "女"}:
        raise validation_error("birth_info.gender", "gender must be one of: 男, 女")

    calendar = str(raw_birth_info.get("calendar", "")).strip().lower()
    if calendar not in {"solar", "lunar"}:
        raise validation_error("birth_info.calendar", "calendar must be one of: solar, lunar")

    return {
        "date": date_value,
        "timezone": timezone,
        "gender": gender,
        "calendar": calendar,
    }


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
    try:
        data = service.get_overview(
            user_id=int(current_user.get("id", 0)),
            is_admin=str(current_user.get("role", "")) == "admin",
            result_id=result_id,
        )
    except AppError as exc:
        if exc.code == "A4004":
            # 用户尚未有可用于生成K线/日历的分析档案时，返回空数据而非404。
            return success_response(data=None)
        raise
    return success_response(data=data)


@insights_bp.post("/insights/overview")
@require_auth()
def generate_insight_overview_by_birth_info():
    payload = request.get_json(silent=True) or {}
    birth_info = _validate_birth_info(payload)

    current_user = getattr(g, "current_user", None) or {}
    data = get_insight_service().get_overview(
        user_id=int(current_user.get("id", 0)),
        is_admin=str(current_user.get("role", "")) == "admin",
        birth_info_override=birth_info,
    )
    return success_response(data=data)
