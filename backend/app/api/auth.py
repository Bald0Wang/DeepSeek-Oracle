from flask import Blueprint, g, request

from app.schemas import (
    validate_forgot_password_payload,
    validate_login_payload,
    validate_register_payload,
    validate_reset_password_payload,
    validate_send_register_code_payload,
)
from app.services.auth_service import get_auth_service
from app.utils.auth import require_auth
from app.utils.response import success_response


auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/auth/register")
def register():
    payload = request.get_json(silent=True) or {}
    normalized = validate_register_payload(payload)
    data = get_auth_service().register(**normalized)
    g.current_user = data.get("user")
    return success_response(message="registered", data=data, status=201)


@auth_bp.post("/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    normalized = validate_login_payload(payload)
    data = get_auth_service().login(**normalized)
    g.current_user = data.get("user")
    return success_response(message="logged_in", data=data)


@auth_bp.post("/auth/register/send-code")
def send_register_code():
    payload = request.get_json(silent=True) or {}
    normalized = validate_send_register_code_payload(payload)
    data = get_auth_service().send_register_code(**normalized)
    return success_response(message="register_code_sent", data=data)


@auth_bp.post("/auth/password/forgot")
def forgot_password():
    payload = request.get_json(silent=True) or {}
    normalized = validate_forgot_password_payload(payload)
    data = get_auth_service().send_reset_password_code(**normalized)
    return success_response(message="reset_code_sent", data=data)


@auth_bp.post("/auth/password/reset")
def reset_password():
    payload = request.get_json(silent=True) or {}
    normalized = validate_reset_password_payload(payload)
    data = get_auth_service().reset_password(**normalized)
    return success_response(message="password_reset", data=data)


@auth_bp.get("/auth/me")
@require_auth()
def me():
    user = getattr(g, "current_user", None)
    return success_response(data={"user": user})


@auth_bp.post("/auth/logout")
@require_auth()
def logout():
    return success_response(message="logged_out", data={"ok": True})
