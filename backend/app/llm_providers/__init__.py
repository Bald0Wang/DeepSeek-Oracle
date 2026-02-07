from flask import current_app

from app.utils.errors import business_error

from .aliyun import AliyunProvider
from .base import BaseLLMProvider
from .deepseek import DeepSeekProvider
from .glm import GLMProvider
from .mock import MockProvider
from .qwen import QwenProvider
from .volcano import VolcanoProvider


def create_provider(provider_name: str, model: str | None = None) -> BaseLLMProvider:
    provider_name = (provider_name or "").strip().lower()
    model = model or current_app.config["LLM_MODEL"]

    if provider_name == "volcano":
        api_key = current_app.config.get("VOLCANO_API_KEY", "")
        if not api_key:
            raise business_error("A3002", "volcano api key is not configured", 502, True)
        provider_model = current_app.config.get("VOLCANO_MODEL") or model
        return VolcanoProvider(api_key=api_key, model=provider_model)

    if provider_name == "aliyun":
        api_key = current_app.config.get("ALIYUN_API_KEY", "")
        if not api_key:
            raise business_error("A3002", "aliyun api key is not configured", 502, True)
        return AliyunProvider(
            api_key=api_key,
            base_url=current_app.config.get("ALIYUN_BASE_URL", ""),
            model=model,
        )

    if provider_name == "deepseek":
        api_key = current_app.config.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise business_error("A3002", "deepseek api key is not configured", 502, True)
        return DeepSeekProvider(
            api_key=api_key,
            base_url=current_app.config.get("DEEPSEEK_BASE_URL", ""),
            model=model,
        )

    if provider_name == "glm":
        api_key = current_app.config.get("ZHIPU_API_KEY", "")
        if not api_key:
            raise business_error("A3002", "zhipu api key is not configured", 502, True)
        return GLMProvider(api_key=api_key, model=model)

    if provider_name == "qwen":
        api_key = current_app.config.get("QWEN_API_KEY", "")
        if not api_key:
            raise business_error("A3002", "qwen api key is not configured", 502, True)
        return QwenProvider(
            api_key=api_key,
            base_url=current_app.config.get("QWEN_BASE_URL", ""),
            model=model,
        )

    if provider_name == "mock":
        return MockProvider(model=model)

    raise business_error("A1002", f"unknown provider: {provider_name}", 422, False)
