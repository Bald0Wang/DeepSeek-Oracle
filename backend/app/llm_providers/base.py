from abc import ABC, abstractmethod
from dataclasses import dataclass

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


class BaseLLMProvider(ABC):
    SYSTEM_PROMPT = "你是一个熟练紫微斗数的大师，请根据用户需求进行紫微斗数命盘分析。"

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

    @abstractmethod
    def generate(self, user_message: str, timeout_s: int = 1800) -> LLMResult:
        raise NotImplementedError
