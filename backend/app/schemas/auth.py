import re

from app.utils.errors import validation_error


EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _validate_email(payload: dict) -> str:
    email = str(payload.get("email", "")).strip().lower()
    if not email:
        raise validation_error("email", "email is required")
    if not EMAIL_PATTERN.match(email):
        raise validation_error("email", "invalid email format")
    return email


def _validate_password(raw_password: str, field_name: str = "password") -> str:
    password = str(raw_password or "").strip()
    if len(password) < 6:
        raise validation_error(field_name, f"{field_name} must be at least 6 characters")
    if len(password) > 128:
        raise validation_error(field_name, f"{field_name} is too long")
    return password


def _validate_code(raw_code: str, field_name: str) -> str:
    code = str(raw_code or "").strip()
    if not code:
        raise validation_error(field_name, f"{field_name} is required")
    if len(code) > 16:
        raise validation_error(field_name, f"{field_name} is too long")
    return code


def validate_send_register_code_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise validation_error("body", "invalid json body")
    return {"email": _validate_email(payload)}


def validate_send_admin_login_code_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise validation_error("body", "invalid json body")
    return {"email": _validate_email(payload)}


def validate_register_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise validation_error("body", "invalid json body")

    email = _validate_email(payload)
    password = _validate_password(payload.get("password"), "password")
    raw_email_code = payload.get("email_code")
    email_code = str(raw_email_code or "").strip()
    if email_code and len(email_code) > 16:
        raise validation_error("email_code", "email_code is too long")

    invite_code = payload.get("invite_code")
    if invite_code is not None:
        invite_code = str(invite_code).strip()
        if len(invite_code) > 64:
            raise validation_error("invite_code", "invite_code is too long")
    else:
        invite_code = ""

    return {
        "email": email,
        "password": password,
        "email_code": email_code,
        "invite_code": invite_code,
    }


def validate_login_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise validation_error("body", "invalid json body")

    email = _validate_email(payload)
    password = str(payload.get("password", "")).strip()

    if not password:
        raise validation_error("password", "password is required")

    return {"email": email, "password": password}


def validate_admin_code_login_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise validation_error("body", "invalid json body")

    email = _validate_email(payload)
    login_code = _validate_code(payload.get("login_code"), "login_code")
    return {"email": email, "login_code": login_code}


def validate_forgot_password_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise validation_error("body", "invalid json body")
    return {"email": _validate_email(payload)}


def validate_reset_password_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise validation_error("body", "invalid json body")

    email = _validate_email(payload)
    reset_code = _validate_code(payload.get("reset_code"), "reset_code")
    new_password = _validate_password(payload.get("new_password"), "new_password")
    return {
        "email": email,
        "reset_code": reset_code,
        "new_password": new_password,
    }
