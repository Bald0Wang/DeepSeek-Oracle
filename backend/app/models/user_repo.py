from __future__ import annotations

from typing import Any

from .database import db_cursor


def _row_to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


class UserRepo:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def create_user(
        self,
        email: str,
        password_hash: str,
        role: str = "user",
        invite_code_used: str | None = None,
    ) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                INSERT INTO users (email, password_hash, role, invite_code_used)
                VALUES (?, ?, ?, ?)
                """,
                (email, password_hash, role, invite_code_used),
            )
        return self.get_by_email(email)

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute("SELECT * FROM users WHERE email = ? LIMIT 1", (email,))
            row = cursor.fetchone()
        return _row_to_dict(row)

    def get_by_id(self, user_id: int) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute("SELECT * FROM users WHERE id = ? LIMIT 1", (user_id,))
            row = cursor.fetchone()
        return _row_to_dict(row)

    def count_admins(self) -> int:
        with db_cursor(self.database_path) as cursor:
            cursor.execute("SELECT COUNT(1) AS total FROM users WHERE role = 'admin' AND is_active = 1")
            row = cursor.fetchone()
        return int(row["total"]) if row else 0

    def count_users(self) -> int:
        with db_cursor(self.database_path) as cursor:
            cursor.execute("SELECT COUNT(1) AS total FROM users")
            row = cursor.fetchone()
        return int(row["total"]) if row else 0

    def update_last_login(self, user_id: int) -> None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                UPDATE users
                SET last_login_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (user_id,),
            )

    def update_password(self, user_id: int, password_hash: str) -> None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                UPDATE users
                SET password_hash = ?
                WHERE id = ?
                """,
                (password_hash, user_id),
            )

    def list_users(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        offset = (page - 1) * page_size

        with db_cursor(self.database_path) as cursor:
            cursor.execute("SELECT COUNT(1) AS total FROM users")
            total = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT id, email, role, is_active, invite_code_used, last_login_at, created_at
                FROM users
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (page_size, offset),
            )
            rows = cursor.fetchall()

        items: list[dict[str, Any]] = []
        for row in rows:
            item = _row_to_dict(row)
            if not item:
                continue
            item["is_active"] = bool(item["is_active"])
            items.append(item)

        return {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "has_next": offset + page_size < total,
            },
        }
