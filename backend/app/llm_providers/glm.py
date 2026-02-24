import time

from zai import ZhipuAiClient

from .base import BaseLLMProvider, LLMResult, LLMUsage, UnsupportedToolCallingError


class GLMProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "glm-5"):
        super().__init__(model=model)
        self.client = ZhipuAiClient(api_key=api_key)

    def generate(self, user_message: str, timeout_s: int = 1800) -> LLMResult:
        _ = timeout_s
        start = time.perf_counter()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            # For divination pages we need direct answer text, not only reasoning trace.
            thinking={"type": "disabled"},
            max_tokens=4096,
            temperature=0.9,
        )
        choice = response.choices[0]
        message = getattr(choice, "message", None)
        if isinstance(message, dict):
            content = str(message.get("content", "") or "")
            if not content:
                content = str(message.get("reasoning_content", "") or "")
        else:
            content = str(getattr(message, "content", "") or "")
            if not content:
                content = str(getattr(message, "reasoning_content", "") or "")
        latency_ms = int((time.perf_counter() - start) * 1000)

        usage_obj = getattr(response, "usage", None)
        if usage_obj:
            usage = LLMUsage(
                input_tokens=int(getattr(usage_obj, "prompt_tokens", 0)),
                output_tokens=int(getattr(usage_obj, "completion_tokens", 0)),
                total_tokens=int(getattr(usage_obj, "total_tokens", 0)),
            )
        else:
            usage = self._usage_from_text(user_message, content)

        finish_reason = getattr(choice, "finish_reason", None)
        return LLMResult(
            content=content,
            usage=usage,
            latency_ms=latency_ms,
            provider="glm",
            model=self.model,
            finish_reason=finish_reason,
        )

    def chat_with_tools(self, messages: list[dict], tools: list[dict], timeout_s: int = 1800):
        _ = (messages, tools, timeout_s)
        raise UnsupportedToolCallingError("provider glm does not support tool calling in current integration")
