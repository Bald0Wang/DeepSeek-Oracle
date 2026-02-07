from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppError(Exception):
    code: str
    message: str
    http_status: int
    retryable: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def validation_error(field: str, message: str) -> AppError:
    return AppError(
        code="A1001",
        message=message,
        http_status=400,
        retryable=False,
        details={"field": field},
    )


def business_error(code: str, message: str, http_status: int, retryable: bool = False) -> AppError:
    return AppError(
        code=code,
        message=message,
        http_status=http_status,
        retryable=retryable,
    )
