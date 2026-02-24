from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask import current_app

from app.models import UserLLMSettingsRepo
from app.utils.errors import business_error


SUPPORTED_PROVIDERS = ("glm", "volcano", "deepseek", "qwen", "aliyun")
SYSTEM_MODELS: dict[str, list[str]] = {
    "glm": ["glm-5", "glm-4.7", "glm-4-plus"],
    "volcano": ["doubao-seed-1-8-251228"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
    "qwen": ["qwen3-max", "qwen-max-latest"],
    "aliyun": ["deepseek-r1"],
}
PROVIDER_LABELS = {
    "glm": "智谱 GLM",
    "volcano": "火山 Ark",
    "deepseek": "DeepSeek",
    "qwen": "通义千问",
    "aliyun": "阿里云兼容",
}
PROVIDER_KEY_MAP: dict[str, tuple[str, str | None]] = {
    "glm": ("ZHIPU_API_KEY", None),
    "volcano": ("VOLCANO_API_KEY", None),
    "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"),
    "qwen": ("QWEN_API_KEY", "QWEN_BASE_URL"),
    "aliyun": ("ALIYUN_API_KEY", "ALIYUN_BASE_URL"),
}


class LLMSettingsService:
    def __init__(self, database_path: str, default_provider: str, default_model: str):
        self.repo = UserLLMSettingsRepo(database_path)
        self.default_provider = (default_provider or "glm").strip().lower()
        self.default_model = (default_model or "glm-5").strip()

    def get_user_config(self, user_id: int) -> dict[str, Any]:
        row = self.repo.get_by_user_id(user_id)
        setting = self._normalize_setting_row(row)
        return {
            "defaults": {
                "provider": self.default_provider,
                "model": self.default_model,
            },
            "provider_options": self._provider_options(),
            "setting": setting,
        }

    def update_user_config(self, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        mode = str(payload.get("mode", "system")).strip().lower()
        provider = str(payload.get("provider") or self.default_provider).strip().lower()
        model = str(payload.get("model") or self.default_model).strip()
        api_key_raw = payload.get("api_key")
        base_url_raw = payload.get("base_url")
        api_key = str(api_key_raw).strip() if api_key_raw is not None else None
        base_url = str(base_url_raw).strip() if base_url_raw is not None else None

        if mode not in {"system", "custom"}:
            raise business_error("A1002", "mode must be system or custom", 422, False)
        if provider not in SUPPORTED_PROVIDERS:
            raise business_error("A1002", f"unsupported provider: {provider}", 422, False)
        if not model:
            raise business_error("A1002", "model is required", 422, False)

        existing = self.repo.get_by_user_id(user_id)
        if mode == "custom":
            api_key = self._resolve_api_key_for_custom(
                existing=existing,
                provider=provider,
                api_key=api_key,
            )
            if provider in {"deepseek", "qwen", "aliyun"}:
                if not base_url and existing and str(existing.get("provider")) == provider:
                    base_url = str(existing.get("base_url") or "").strip() or None
            else:
                base_url = None
        else:
            api_key = None
            base_url = None

        updated = self.repo.upsert(
            user_id=user_id,
            mode=mode,
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
        return self._normalize_setting_row(updated)

    def resolve_runtime_config(
        self,
        *,
        user_id: int | None,
        provider_override: str | None = None,
        model_override: str | None = None,
        base_config: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved_base = self._base_provider_config(base_config)
        setting_row = self.repo.get_by_user_id(int(user_id or 0)) if user_id else None
        setting = self._normalize_setting_row(setting_row)

        provider = (
            str(provider_override).strip().lower()
            if provider_override and str(provider_override).strip()
            else setting["provider"]
        )
        model = (
            str(model_override).strip()
            if model_override and str(model_override).strip()
            else setting["model"]
        )

        if provider not in SUPPORTED_PROVIDERS:
            provider = self.default_provider
        if not model:
            model = self.default_model

        source = "default"
        if setting_row:
            source = "user_setting"
        if provider_override or model_override:
            source = "request_override"

        if (
            setting["mode"] == "custom"
            and setting.get("has_api_key")
            and provider == setting["provider"]
        ):
            key_name, base_url_name = PROVIDER_KEY_MAP[provider]
            resolved_base[key_name] = str(setting_row.get("api_key") or "")
            if base_url_name:
                custom_base_url = str(setting_row.get("base_url") or "").strip()
                if custom_base_url:
                    resolved_base[base_url_name] = custom_base_url

        if provider == "volcano":
            resolved_base["VOLCANO_MODEL"] = model
        resolved_base["LLM_MODEL"] = model

        return {
            "provider": provider,
            "model": model,
            "provider_config": resolved_base,
            "source": source,
        }

    def _resolve_api_key_for_custom(
        self,
        *,
        existing: dict[str, Any] | None,
        provider: str,
        api_key: str | None,
    ) -> str:
        normalized = (api_key or "").strip()
        if normalized:
            return normalized
        if existing and str(existing.get("provider") or "").strip().lower() == provider:
            kept = str(existing.get("api_key") or "").strip()
            if kept:
                return kept
        raise business_error("A1002", "custom mode requires api_key", 422, False)

    def _normalize_setting_row(self, row: dict[str, Any] | None) -> dict[str, Any]:
        if not row:
            return {
                "mode": "system",
                "provider": self.default_provider,
                "model": self.default_model,
                "base_url": None,
                "has_api_key": False,
                "updated_at": None,
            }
        return {
            "mode": str(row.get("mode") or "system").strip().lower() or "system",
            "provider": str(row.get("provider") or self.default_provider).strip().lower() or self.default_provider,
            "model": str(row.get("model") or self.default_model).strip() or self.default_model,
            "base_url": str(row.get("base_url") or "").strip() or None,
            "has_api_key": bool(str(row.get("api_key") or "").strip()),
            "updated_at": row.get("updated_at"),
        }

    def _provider_options(self) -> list[dict[str, Any]]:
        options: list[dict[str, Any]] = []
        for provider in SUPPORTED_PROVIDERS:
            options.append(
                {
                    "provider": provider,
                    "label": PROVIDER_LABELS.get(provider, provider),
                    "system_models": SYSTEM_MODELS.get(provider, []),
                    "supports_base_url": provider in {"deepseek", "qwen", "aliyun"},
                }
            )
        return options

    @staticmethod
    def _base_provider_config(base_config: Mapping[str, Any] | None = None) -> dict[str, Any]:
        config = base_config or current_app.config
        return {
            "LLM_MODEL": str(config.get("LLM_MODEL", "")),
            "VOLCANO_API_KEY": str(config.get("VOLCANO_API_KEY", "")),
            "VOLCANO_MODEL": str(config.get("VOLCANO_MODEL", "")),
            "ALIYUN_API_KEY": str(config.get("ALIYUN_API_KEY", "")),
            "ALIYUN_BASE_URL": str(config.get("ALIYUN_BASE_URL", "")),
            "DEEPSEEK_API_KEY": str(config.get("DEEPSEEK_API_KEY", "")),
            "DEEPSEEK_BASE_URL": str(config.get("DEEPSEEK_BASE_URL", "")),
            "ZHIPU_API_KEY": str(config.get("ZHIPU_API_KEY", "")),
            "QWEN_API_KEY": str(config.get("QWEN_API_KEY", "")),
            "QWEN_BASE_URL": str(config.get("QWEN_BASE_URL", "")),
        }


def get_llm_settings_service() -> LLMSettingsService:
    service = current_app.extensions.get("llm_settings_service")
    if service:
        return service

    service = LLMSettingsService(
        database_path=current_app.config["DATABASE_PATH"],
        default_provider=current_app.config["LLM_PROVIDER"],
        default_model=current_app.config["LLM_MODEL"],
    )
    current_app.extensions["llm_settings_service"] = service
    return service

