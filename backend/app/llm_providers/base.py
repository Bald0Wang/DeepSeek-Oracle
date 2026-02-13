from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.utils.tokenizer import count_tokens


@dataclass
class LLMUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass
class LLMResult:
    content: str
    usage: LLMUsage
    latency_ms: int
    provider: str
    model: str
    finish_reason: str | None = None


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolChatResult:
    content: str
    tool_calls: list[ToolCall]
    usage: LLMUsage
    latency_ms: int
    provider: str
    model: str
    finish_reason: str | None = None


class UnsupportedToolCallingError(RuntimeError):
    pass


class BaseLLMProvider(ABC):
    SYSTEM_PROMPT = (
        "你是一位精通东方命理学的智慧顾问，擅长紫微斗数和梅花易数。"
        "你用现代语言表达传统智慧，注重给出可执行的建议。"
        "你不做确定性断言，不渲染灾祸，始终引导用户独立思考和行动。"
    )

    def __init__(self, model: str):
        self.model = model

    def _usage_from_text(self, user_message: str, content: str) -> LLMUsage:
        input_tokens = count_tokens(user_message)
        output_tokens = count_tokens(content)
        return LLMUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )

    def _usage_from_messages(self, messages: list[dict[str, Any]], content: str) -> LLMUsage:
        message_text = "\n".join(str(item.get("content", "")) for item in messages)
        return self._usage_from_text(message_text, content)

    @abstractmethod
    def generate(self, user_message: str, timeout_s: int = 1800) -> LLMResult:
        raise NotImplementedError

    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        timeout_s: int = 1800,
    ) -> ToolChatResult:
        raise UnsupportedToolCallingError(f"provider {self.__class__.__name__} does not support tool calling")
