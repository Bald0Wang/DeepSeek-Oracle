import time

from openai import OpenAI

from .base import BaseLLMProvider, LLMResult, LLMUsage


class DeepSeekProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-chat"):
        super().__init__(model=model)
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, user_message: str, timeout_s: int = 1800) -> LLMResult:
        start = time.perf_counter()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            stream=False,
            timeout=timeout_s,
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
            provider="deepseek",
            model=self.model,
            finish_reason=finish_reason,
        )
