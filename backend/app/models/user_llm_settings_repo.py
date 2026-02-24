from __future__ import annotations

from typing import Any

from .database import db_cursor


def _row_to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


class UserLLMSettingsRepo:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def get_by_user_id(self, user_id: int) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                SELECT id, user_id, mode, provider, model, api_key, base_url, created_at, updated_at
                FROM user_llm_settings
                WHERE user_id = ?
                LIMIT 1
                """,
                (user_id,),
            )
            row = cursor.fetchone()
        return _row_to_dict(row)

    def upsert(
        self,
        *,
        user_id: int,
        mode: str,
        provider: str,
        model: str,
        api_key: str | None,
        base_url: str | None,
    ) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                INSERT INTO user_llm_settings (user_id, mode, provider, model, api_key, base_url)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                  mode = excluded.mode,
                  provider = excluded.provider,
                  model = excluded.model,
                  api_key = excluded.api_key,
                  base_url = excluded.base_url,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, mode, provider, model, api_key, base_url),
            )
        return self.get_by_user_id(user_id)

