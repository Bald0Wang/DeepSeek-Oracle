import time

from .base import BaseLLMProvider, LLMResult, UnsupportedToolCallingError


class MockProvider(BaseLLMProvider):
    def __init__(self, model: str = "mock-v1"):
        super().__init__(model=model)

    def generate(self, user_message: str, timeout_s: int = 1800) -> LLMResult:
        start = time.perf_counter()
        content = (
            "[mock response] this is a placeholder analysis result for local architecture testing.\n\n"
            f"input digest: {user_message[:80]}"
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        usage = self._usage_from_text(user_message, content)
        return LLMResult(
            content=content,
            usage=usage,
            latency_ms=latency_ms,
            provider="mock",
            model=self.model,
            finish_reason="stop",
        )

    def chat_with_tools(self, messages: list[dict], tools: list[dict], timeout_s: int = 1800):
        _ = (messages, tools, timeout_s)
        raise UnsupportedToolCallingError("provider mock does not support tool calling")
