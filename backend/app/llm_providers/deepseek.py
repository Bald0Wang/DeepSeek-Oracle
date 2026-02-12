import json
import time
import uuid

from openai import OpenAI

from .base import BaseLLMProvider, LLMResult, LLMUsage, ToolCall, ToolChatResult


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

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        timeout_s: int = 1800,
    ) -> ToolChatResult:
        start = time.perf_counter()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=False,
            timeout=timeout_s,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        message = response.choices[0].message
        content = message.content or ""

        tool_calls: list[ToolCall] = []
        raw_calls = getattr(message, "tool_calls", None) or []
        for raw_call in raw_calls:
            raw_function = getattr(raw_call, "function", None)
            if not raw_function:
                continue
            raw_args = getattr(raw_function, "arguments", "") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else {}
            except Exception:
                args = {}

            call_id = getattr(raw_call, "id", "") or f"call_{uuid.uuid4().hex[:10]}"
            tool_calls.append(
                ToolCall(
                    id=call_id,
                    name=str(getattr(raw_function, "name", "")).strip(),
                    arguments=args if isinstance(args, dict) else {},
                )
            )

        usage_obj = getattr(response, "usage", None)
        if usage_obj:
            usage = LLMUsage(
                input_tokens=int(getattr(usage_obj, "prompt_tokens", 0)),
                output_tokens=int(getattr(usage_obj, "completion_tokens", 0)),
                total_tokens=int(getattr(usage_obj, "total_tokens", 0)),
            )
        else:
            usage = self._usage_from_messages(messages=messages, content=content)

        finish_reason = response.choices[0].finish_reason
        return ToolChatResult(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            latency_ms=latency_ms,
            provider="deepseek",
            model=self.model,
            finish_reason=finish_reason,
        )
