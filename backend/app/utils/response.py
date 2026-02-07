from typing import Any

from flask import g, jsonify


def success_response(
    data: Any = None,
    message: str = "ok",
    code: int = 0,
    status: int = 200,
):
    payload = {
        "code": code,
        "message": message,
        "data": data,
        "request_id": getattr(g, "request_id", ""),
    }
    return jsonify(payload), status


def error_response(
    code: str,
    message: str,
    status: int,
    details: dict[str, Any] | None = None,
    retryable: bool = False,
):
    payload = {
        "code": code,
        "message": message,
        "details": details or {},
        "retryable": retryable,
        "request_id": getattr(g, "request_id", ""),
    }
    return jsonify(payload), status
