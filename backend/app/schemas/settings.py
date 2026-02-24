from __future__ import annotations

from app.services.llm_settings_service import SUPPORTED_PROVIDERS
from app.utils.errors import validation_error


def validate_update_llm_settings_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise validation_error("body", "invalid json body")

    mode = str(payload.get("mode", "system")).strip().lower()
    if mode not in {"system", "custom"}:
        raise validation_error("mode", "mode must be system or custom")

    provider = str(payload.get("provider", "")).strip().lower()
    if not provider:
        raise validation_error("provider", "provider is required")
    if provider not in SUPPORTED_PROVIDERS:
        raise validation_error("provider", f"provider must be one of: {', '.join(SUPPORTED_PROVIDERS)}")

    model = str(payload.get("model", "")).strip()
    if not model:
        raise validation_error("model", "model is required")
    if len(model) > 120:
        raise validation_error("model", "model is too long")

    api_key_raw = payload.get("api_key")
    base_url_raw = payload.get("base_url")
    if api_key_raw is not None and not isinstance(api_key_raw, str):
        raise validation_error("api_key", "api_key must be string")
    if base_url_raw is not None and not isinstance(base_url_raw, str):
        raise validation_error("base_url", "base_url must be string")

    normalized = {
        "mode": mode,
        "provider": provider,
        "model": model,
    }
    if api_key_raw is not None:
        normalized["api_key"] = str(api_key_raw).strip()
    if base_url_raw is not None:
        base_url = str(base_url_raw).strip()
        if len(base_url) > 255:
            raise validation_error("base_url", "base_url is too long")
        normalized["base_url"] = base_url
    return normalized

