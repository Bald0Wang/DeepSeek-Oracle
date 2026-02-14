from __future__ import annotations

from functools import wraps

from flask import g, request

from app.services.auth_service import get_auth_service
from app.utils.errors import business_error


def _extract_bearer_token() -> str:
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header:
        return ""
    parts = auth_header.split(" ", 1)
    if len(parts) != 2:
        return ""
    scheme, token = parts
    if scheme.lower() != "bearer":
        return ""
    return token.strip()


def resolve_request_user(optional: bool = False):
    token = _extract_bearer_token()
    if not token:
        g.current_user = None
        if optional:
            return None
        raise business_error("A4011", "missing access token", 401, False)

    user = get_auth_service().authenticate_token(token)
    g.current_user = user
    return user


def require_auth(admin_only: bool = False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = resolve_request_user(optional=False)

            if admin_only and user.get("role") != "admin":
                raise business_error("A4013", "admin permission required", 403, False)
            return func(*args, **kwargs)

        return wrapper

    return decorator
