from __future__ import annotations

from datetime import datetime

from app.utils.errors import validation_error


ALLOWED_CALENDARS = {"solar", "lunar"}
ALLOWED_GENDERS = {"男", "女"}


def _optional_text(payload: dict, field: str, max_length: int) -> str:
    value = payload.get(field, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise validation_error(field, f"{field} must be string")
    normalized = value.strip()
    if len(normalized) > max_length:
        raise validation_error(field, f"{field} is too long")
    return normalized


def _required_birth_info(payload: dict) -> dict:
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
    if gender not in ALLOWED_GENDERS:
        raise validation_error("birth_info.gender", "gender must be one of: 男, 女")

    calendar = str(raw_birth_info.get("calendar", "")).strip().lower()
    if calendar not in ALLOWED_CALENDARS:
        raise validation_error("birth_info.calendar", "calendar must be one of: solar, lunar")

    return {
        "date": date_value,
        "timezone": timezone,
        "gender": gender,
        "calendar": calendar,
    }


def validate_ziwei_divination_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise validation_error("body", "invalid json body")

    normalized = {
        "question": _optional_text(payload, "question", 2000) or "请给我一份紫微斗数长线解读与行动建议。",
        "birth_info": _required_birth_info(payload),
    }

    provider = _optional_text(payload, "provider", 50)
    model = _optional_text(payload, "model", 120)
    if provider:
        normalized["provider"] = provider
    if model:
        normalized["model"] = model
    return normalized


def validate_meihua_divination_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise validation_error("body", "invalid json body")

    topic = _optional_text(payload, "topic", 500)
    if not topic:
        raise validation_error("topic", "topic is required")

    occurred_at_raw = _optional_text(payload, "occurred_at", 40)
    if occurred_at_raw:
        try:
            occurred_at = datetime.fromisoformat(occurred_at_raw)
        except ValueError as exc:
            raise validation_error("occurred_at", "occurred_at must be ISO datetime") from exc
    else:
        occurred_at = datetime.now()

    normalized = {
        "topic": topic,
        "occurred_at": occurred_at.replace(second=0, microsecond=0).isoformat(),
    }

    provider = _optional_text(payload, "provider", 50)
    model = _optional_text(payload, "model", 120)
    if provider:
        normalized["provider"] = provider
    if model:
        normalized["model"] = model
    return normalized
