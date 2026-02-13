from __future__ import annotations

from datetime import datetime

from app.utils.errors import validation_error


ALLOWED_SELECTED_SCHOOLS = {"east", "west", "mixed"}
ALLOWED_ENABLED_SCHOOLS = {
    "ziwei",
    "meihua",
    "tarot",
    "daily_card",
    "actionizer",
    "philosophy",
}
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


def _optional_birth_info(payload: dict) -> dict | None:
    raw_birth_info = payload.get("birth_info")
    if raw_birth_info is None:
        return None
    if not isinstance(raw_birth_info, dict):
        raise validation_error("birth_info", "birth_info must be object")

    required = ["date", "timezone", "gender", "calendar"]
    for field in required:
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


def validate_oracle_chat_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise validation_error("body", "invalid json body")

    user_query = _optional_text(payload, "user_query", 2000)
    if not user_query:
        raise validation_error("user_query", "user_query is required")

    selected_school = str(payload.get("selected_school", "east")).strip().lower() or "east"
    if selected_school not in ALLOWED_SELECTED_SCHOOLS:
        raise validation_error("selected_school", "selected_school must be east/west/mixed")

    enabled_schools_value = payload.get("enabled_schools", [])
    enabled_schools: list[str] = []
    if enabled_schools_value is not None:
        if not isinstance(enabled_schools_value, list):
            raise validation_error("enabled_schools", "enabled_schools must be an array")
        for index, item in enumerate(enabled_schools_value):
            value = str(item).strip().lower()
            if value not in ALLOWED_ENABLED_SCHOOLS:
                raise validation_error(
                    "enabled_schools",
                    f"enabled_schools[{index}] must be one of: {', '.join(sorted(ALLOWED_ENABLED_SCHOOLS))}",
                )
            if value not in enabled_schools:
                enabled_schools.append(value)

    safety_policy = payload.get("safety_policy", {})
    if safety_policy is None:
        safety_policy = {}
    if not isinstance(safety_policy, dict):
        raise validation_error("safety_policy", "safety_policy must be object")

    normalized = {
        "user_query": user_query,
        "conversation_history_summary": _optional_text(payload, "conversation_history_summary", 6000),
        "user_profile_summary": _optional_text(payload, "user_profile_summary", 6000),
        "selected_school": selected_school,
        "enabled_schools": enabled_schools,
        "safety_policy": safety_policy,
        "birth_info": _optional_birth_info(payload),
    }

    conversation_id = payload.get("conversation_id")
    if conversation_id is not None:
        try:
            conversation_id_value = int(conversation_id)
        except (TypeError, ValueError) as exc:
            raise validation_error("conversation_id", "conversation_id must be integer") from exc
        if conversation_id_value <= 0:
            raise validation_error("conversation_id", "conversation_id must be positive")
        normalized["conversation_id"] = conversation_id_value

    provider = payload.get("provider")
    model = payload.get("model")
    if provider is not None:
        provider_value = str(provider).strip()
        if provider_value:
            normalized["provider"] = provider_value
    if model is not None:
        model_value = str(model).strip()
        if model_value:
            normalized["model"] = model_value

    return normalized
