from __future__ import annotations

import hashlib
import secrets

from flask import current_app
from itsdangerous import BadData, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app.models import UserRepo, VerificationCodeRepo
from app.services.email_service import get_email_service
from app.utils.errors import business_error

REGISTER_PURPOSE = "register"
RESET_PASSWORD_PURPOSE = "reset_password"


class AuthService:
    def __init__(
        self,
        *,
        database_path: str,
        secret_key: str,
        token_expire_hours: int,
        invite_only: bool,
        invite_codes: list[str],
        admin_emails: list[str],
        email_verify_required: bool,
        email_code_expire_minutes: int,
    ):
        self.user_repo = UserRepo(database_path)
        self.verification_code_repo = VerificationCodeRepo(database_path)
        self.serializer = URLSafeTimedSerializer(secret_key=secret_key, salt="oracle-auth")
        self.token_expire_seconds = max(token_expire_hours, 1) * 3600
        self.invite_only = invite_only
        self.invite_codes = {code.strip().upper() for code in invite_codes if code.strip()}
        self.admin_emails = {email.strip().lower() for email in admin_emails if email.strip()}
        self.email_verify_required = email_verify_required
        self.email_code_expire_minutes = max(email_code_expire_minutes, 1)

    def send_register_code(self, email: str) -> dict:
        if self.user_repo.get_by_email(email):
            raise business_error("A4009", "email already registered", 409, False)

        code = self._generate_verification_code()
        self.verification_code_repo.create_code(
            email=email,
            purpose=REGISTER_PURPOSE,
            code_hash=self._hash_verification_code(email=email, purpose=REGISTER_PURPOSE, code=code),
            expire_minutes=self.email_code_expire_minutes,
        )
        self._send_code_email(
            to_email=email,
            subject="DeepSeek Oracle 注册验证码",
            code=code,
            expire_minutes=self.email_code_expire_minutes,
            scene_text="注册",
        )
        return {"sent": True, "expire_minutes": self.email_code_expire_minutes}

    def register(self, email: str, password: str, invite_code: str = "", email_code: str = "") -> dict:
        if self.user_repo.get_by_email(email):
            raise business_error("A4009", "email already registered", 409, False)

        if self.email_verify_required:
            normalized_email_code = email_code.strip()
            if not normalized_email_code:
                raise business_error("A4014", "email verification code is required", 403, False)
            if not self._consume_code(
                email=email, purpose=REGISTER_PURPOSE, code=normalized_email_code
            ):
                raise business_error("A4014", "invalid or expired email verification code", 403, False)

        if self._invite_required():
            normalized_invite = invite_code.strip().upper()
            if not normalized_invite:
                raise business_error("A4012", "invite code is required", 403, False)
            if normalized_invite not in self.invite_codes:
                raise business_error("A4012", "invalid invite code", 403, False)
        else:
            normalized_invite = invite_code.strip().upper() if invite_code else ""

        role = self._resolve_role(email)
        user = self.user_repo.create_user(
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            invite_code_used=normalized_invite or None,
        )
        if not user:
            raise business_error("A5000", "create user failed", 500, False)

        token = self._build_token(user_id=int(user["id"]), role=str(user["role"]))
        return {"token": token, "user": self._public_user(user)}

    def login(self, email: str, password: str) -> dict:
        user = self.user_repo.get_by_email(email)
        if not user:
            raise business_error("A4010", "invalid email or password", 401, False)
        if not bool(user.get("is_active", 1)):
            raise business_error("A4010", "account is disabled", 403, False)

        if not check_password_hash(user["password_hash"], password):
            raise business_error("A4010", "invalid email or password", 401, False)

        self.user_repo.update_last_login(int(user["id"]))
        refreshed = self.user_repo.get_by_id(int(user["id"])) or user
        token = self._build_token(user_id=int(refreshed["id"]), role=str(refreshed["role"]))
        return {"token": token, "user": self._public_user(refreshed)}

    def send_reset_password_code(self, email: str) -> dict:
        user = self.user_repo.get_by_email(email)
        if not user:
            # Do not reveal whether account exists.
            return {"sent": True, "expire_minutes": self.email_code_expire_minutes}

        code = self._generate_verification_code()
        self.verification_code_repo.create_code(
            email=email,
            purpose=RESET_PASSWORD_PURPOSE,
            code_hash=self._hash_verification_code(
                email=email, purpose=RESET_PASSWORD_PURPOSE, code=code
            ),
            expire_minutes=self.email_code_expire_minutes,
        )
        self._send_code_email(
            to_email=email,
            subject="DeepSeek Oracle 重置密码验证码",
            code=code,
            expire_minutes=self.email_code_expire_minutes,
            scene_text="重置密码",
        )
        return {"sent": True, "expire_minutes": self.email_code_expire_minutes}

    def reset_password(self, email: str, reset_code: str, new_password: str) -> dict:
        user = self.user_repo.get_by_email(email)
        if not user:
            raise business_error("A4015", "invalid or expired reset code", 403, False)
        if not bool(user.get("is_active", 1)):
            raise business_error("A4010", "account is disabled", 403, False)

        if not self._consume_code(email=email, purpose=RESET_PASSWORD_PURPOSE, code=reset_code):
            raise business_error("A4015", "invalid or expired reset code", 403, False)

        self.user_repo.update_password(
            user_id=int(user["id"]), password_hash=generate_password_hash(new_password)
        )
        return {"ok": True}

    def authenticate_token(self, token: str) -> dict:
        try:
            payload = self.serializer.loads(token, max_age=self.token_expire_seconds)
        except SignatureExpired as exc:
            raise business_error("A4011", "token expired", 401, False) from exc
        except BadData as exc:
            raise business_error("A4011", "invalid token", 401, False) from exc

        user_id = int(payload.get("uid", 0))
        if user_id <= 0:
            raise business_error("A4011", "invalid token payload", 401, False)

        user = self.user_repo.get_by_id(user_id)
        if not user or not bool(user.get("is_active", 1)):
            raise business_error("A4010", "account unavailable", 401, False)
        return self._public_user(user)

    def _build_token(self, user_id: int, role: str) -> str:
        return self.serializer.dumps({"uid": user_id, "role": role})

    def _invite_required(self) -> bool:
        return self.invite_only or bool(self.invite_codes)

    def _resolve_role(self, email: str) -> str:
        normalized_email = email.lower()
        if normalized_email in self.admin_emails:
            return "admin"
        if self.user_repo.count_admins() == 0:
            return "admin"
        return "user"

    def _consume_code(self, *, email: str, purpose: str, code: str) -> bool:
        return self.verification_code_repo.consume_valid_code(
            email=email,
            purpose=purpose,
            code_hash=self._hash_verification_code(email=email, purpose=purpose, code=code),
        )

    @staticmethod
    def _generate_verification_code() -> str:
        return f"{secrets.randbelow(1000000):06d}"

    @staticmethod
    def _hash_verification_code(*, email: str, purpose: str, code: str) -> str:
        raw = f"{email.strip().lower()}:{purpose}:{code.strip()}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _public_user(user: dict) -> dict:
        return {
            "id": int(user["id"]),
            "email": str(user["email"]),
            "role": str(user.get("role", "user")),
            "is_active": bool(user.get("is_active", 1)),
            "last_login_at": user.get("last_login_at"),
            "created_at": user.get("created_at"),
        }

    @staticmethod
    def _send_code_email(
        *,
        to_email: str,
        subject: str,
        code: str,
        expire_minutes: int,
        scene_text: str,
    ) -> None:
        content = (
            f"您好，\n\n"
            f"您正在进行 DeepSeek Oracle 的{scene_text}操作。\n"
            f"验证码：{code}\n"
            f"有效期：{expire_minutes} 分钟。\n\n"
            f"若非本人操作，请忽略本邮件。"
        )
        get_email_service().send(to_email=to_email, subject=subject, text_content=content)


def get_auth_service() -> AuthService:
    service = current_app.extensions.get("auth_service")
    if service:
        return service

    service = AuthService(
        database_path=current_app.config["DATABASE_PATH"],
        secret_key=current_app.config["SECRET_KEY"],
        token_expire_hours=current_app.config["AUTH_TOKEN_EXPIRE_HOURS"],
        invite_only=current_app.config["INVITE_ONLY"],
        invite_codes=current_app.config["INVITE_CODES"],
        admin_emails=current_app.config["ADMIN_EMAILS"],
        email_verify_required=current_app.config["EMAIL_VERIFY_REQUIRED"],
        email_code_expire_minutes=current_app.config["EMAIL_CODE_EXPIRE_MINUTES"],
    )
    current_app.extensions["auth_service"] = service
    return service
