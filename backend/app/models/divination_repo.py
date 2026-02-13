import json
from typing import Any

from .database import db_cursor


def _row_to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


class DivinationRepo:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def create_record(
        self,
        *,
        user_id: int,
        divination_type: str,
        question_text: str,
        birth_info: dict[str, Any] | None,
        occurred_at: str | None,
        result_payload: dict[str, Any],
        provider: str,
        model: str,
    ) -> int:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                INSERT INTO divination_records (
                  user_id,
                  divination_type,
                  question_text,
                  birth_info_json,
                  occurred_at,
                  result_json,
                  provider,
                  model
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(user_id),
                    divination_type,
                    question_text.strip(),
                    json.dumps(birth_info, ensure_ascii=False) if birth_info else None,
                    occurred_at,
                    json.dumps(result_payload, ensure_ascii=False),
                    provider,
                    model,
                ),
            )
            return int(cursor.lastrowid or 0)

    def list_records(
        self,
        *,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        divination_type: str | None = None,
    ) -> dict[str, Any]:
        safe_page = max(int(page), 1)
        safe_page_size = min(max(int(page_size), 1), 100)
        offset = (safe_page - 1) * safe_page_size

        where_clause = "WHERE user_id = ?"
        params: list[Any] = [int(user_id)]
        if divination_type in {"ziwei", "meihua"}:
            where_clause += " AND divination_type = ?"
            params.append(divination_type)

        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(1) AS total
                FROM divination_records
                {where_clause}
                """,
                tuple(params),
            )
            total = int(cursor.fetchone()["total"])
            cursor.execute(
                f"""
                SELECT
                  id,
                  divination_type,
                  question_text,
                  occurred_at,
                  provider,
                  model,
                  created_at
                FROM divination_records
                {where_clause}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                tuple([*params, safe_page_size, offset]),
            )
            rows = cursor.fetchall()

        items: list[dict[str, Any]] = []
        for row in rows:
            data = _row_to_dict(row)
            if not data:
                continue
            items.append(
                {
                    "id": data["id"],
                    "type": data["divination_type"],
                    "title": data["question_text"],
                    "occurred_at": data["occurred_at"],
                    "provider": data["provider"],
                    "model": data["model"],
                    "created_at": data["created_at"],
                }
            )

        return {
            "items": items,
            "pagination": {
                "page": safe_page,
                "page_size": safe_page_size,
                "total": total,
                "has_next": offset + safe_page_size < total,
            },
        }

    def get_record(self, *, record_id: int, user_id: int, is_admin: bool = False) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            if is_admin:
                cursor.execute(
                    """
                    SELECT *
                    FROM divination_records
                    WHERE id = ?
                    LIMIT 1
                    """,
                    (int(record_id),),
                )
            else:
                cursor.execute(
                    """
                    SELECT *
                    FROM divination_records
                    WHERE id = ? AND user_id = ?
                    LIMIT 1
                    """,
                    (int(record_id), int(user_id)),
                )
            row = cursor.fetchone()
        data = _row_to_dict(row)
        if not data:
            return None
        try:
            birth_info = json.loads(data["birth_info_json"]) if data.get("birth_info_json") else None
        except json.JSONDecodeError:
            birth_info = None
        try:
            result_payload = json.loads(data.get("result_json") or "{}")
        except json.JSONDecodeError:
            result_payload = {}
        return {
            "id": data["id"],
            "user_id": data["user_id"],
            "type": data["divination_type"],
            "question_text": data["question_text"],
            "birth_info": birth_info,
            "occurred_at": data["occurred_at"],
            "result": result_payload if isinstance(result_payload, dict) else {},
            "provider": data["provider"],
            "model": data["model"],
            "created_at": data["created_at"],
        }
