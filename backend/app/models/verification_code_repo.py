from __future__ import annotations

from .database import db_cursor


class VerificationCodeRepo:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def create_code(self, *, email: str, purpose: str, code_hash: str, expire_minutes: int) -> None:
        minutes = max(expire_minutes, 1)
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                UPDATE email_verification_codes
                SET consumed_at = CURRENT_TIMESTAMP
                WHERE email = ? AND purpose = ? AND consumed_at IS NULL
                """,
                (email, purpose),
            )
            cursor.execute(
                """
                INSERT INTO email_verification_codes (email, purpose, code_hash, expires_at)
                VALUES (?, ?, ?, DATETIME('now', ?))
                """,
                (email, purpose, code_hash, f"+{minutes} minutes"),
            )

    def consume_valid_code(self, *, email: str, purpose: str, code_hash: str) -> bool:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                SELECT id
                FROM email_verification_codes
                WHERE email = ?
                  AND purpose = ?
                  AND code_hash = ?
                  AND consumed_at IS NULL
                  AND expires_at > CURRENT_TIMESTAMP
                ORDER BY id DESC
                LIMIT 1
                """,
                (email, purpose, code_hash),
            )
            row = cursor.fetchone()
            if not row:
                return False

            cursor.execute(
                """
                UPDATE email_verification_codes
                SET consumed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (int(row["id"]),),
            )
            return True
