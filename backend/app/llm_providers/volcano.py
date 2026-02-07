import time

from volcenginesdkarkruntime import Ark

from .base import BaseLLMProvider, LLMResult, LLMUsage


class VolcanoProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str):
        super().__init__(model=model)
        self.client = Ark(api_key=api_key, timeout=1800)

    def generate(self, user_message: str, timeout_s: int = 1800) -> LLMResult:
        start = time.perf_counter()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        content = response.choices[0].message.content or ""
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

        finish_reason = response.choices[0].finish_reason
        return LLMResult(
            content=content,
            usage=usage,
            latency_ms=latency_ms,
            provider="volcano",
            model=self.model,
            finish_reason=finish_reason,
        )
