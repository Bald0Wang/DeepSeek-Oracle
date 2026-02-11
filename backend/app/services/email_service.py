from __future__ import annotations

import smtplib
from email.message import EmailMessage

from flask import current_app

from app.utils.errors import business_error


class EmailService:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool,
        from_email: str,
        from_name: str,
        timeout_s: int = 20,
    ):
        self.host = host.strip()
        self.port = int(port)
        self.username = username.strip()
        self.password = password.strip()
        self.use_ssl = bool(use_ssl)
        self.from_email = from_email.strip() or self.username
        self.from_name = from_name.strip() or "DeepSeek Oracle"
        self.timeout_s = max(int(timeout_s), 5)

    def ensure_configured(self) -> None:
        if not self.host or self.port <= 0:
            raise business_error("A4020", "smtp is not configured", 503, False)
        if not self.username or not self.password:
            raise business_error("A4020", "smtp auth is not configured", 503, False)
        if not self.from_email:
            raise business_error("A4020", "smtp from_email is not configured", 503, False)

    def send(self, *, to_email: str, subject: str, text_content: str) -> None:
        self.ensure_configured()

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = to_email
        message.set_content(text_content)

        try:
            if self.use_ssl:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout_s) as server:
                    server.login(self.username, self.password)
                    server.send_message(message)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=self.timeout_s) as server:
                    server.starttls()
                    server.login(self.username, self.password)
                    server.send_message(message)
        except Exception as exc:
            raise business_error("A4021", f"send email failed: {exc}", 502, True) from exc


def get_email_service() -> EmailService:
    service = current_app.extensions.get("email_service")
    if service:
        return service

    service = EmailService(
        host=current_app.config["SMTP_HOST"],
        port=current_app.config["SMTP_PORT"],
        username=current_app.config["SMTP_USERNAME"],
        password=current_app.config["SMTP_PASSWORD"],
        use_ssl=current_app.config["SMTP_USE_SSL"],
        from_email=current_app.config["SMTP_FROM_EMAIL"],
        from_name=current_app.config["SMTP_FROM_NAME"],
        timeout_s=current_app.config["SMTP_TIMEOUT_S"],
    )
    current_app.extensions["email_service"] = service
    return service
