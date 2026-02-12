import json
import sqlite3
from typing import Any

from .database import db_cursor


def _row_to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


class InsightRepo:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def upsert_life_kline_profile(
        self,
        *,
        user_id: int,
        source_result_id: int | None,
        birth_info: dict[str, Any],
        sparse: dict[str, Any],
        kline: list[dict[str, Any]],
        summary: dict[str, Any],
    ) -> None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                INSERT INTO life_kline_profiles (
                  user_id, source_result_id, birth_info_json, sparse_json, kline_json, summary_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                  source_result_id = excluded.source_result_id,
                  birth_info_json = excluded.birth_info_json,
                  sparse_json = excluded.sparse_json,
                  kline_json = excluded.kline_json,
                  summary_json = excluded.summary_json,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (
                    int(user_id),
                    int(source_result_id) if source_result_id is not None else None,
                    json.dumps(birth_info, ensure_ascii=False),
                    json.dumps(sparse, ensure_ascii=False),
                    json.dumps(kline, ensure_ascii=False),
                    json.dumps(summary, ensure_ascii=False),
                ),
            )

    def get_life_kline_profile(self, *, user_id: int) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM life_kline_profiles
                WHERE user_id = ?
                LIMIT 1
                """,
                (int(user_id),),
            )
            row = cursor.fetchone()
        raw = _row_to_dict(row)
        if not raw:
            return None
        return {
            "source_result_id": raw.get("source_result_id"),
            "birth_info": json.loads(raw.get("birth_info_json") or "{}"),
            "sparse": json.loads(raw.get("sparse_json") or "{}"),
            "kline": json.loads(raw.get("kline_json") or "[]"),
            "summary": json.loads(raw.get("summary_json") or "{}"),
            "updated_at": raw.get("updated_at"),
            "created_at": raw.get("created_at"),
        }

    def upsert_monthly_calendar(
        self,
        *,
        user_id: int,
        month_key: str,
        source_result_id: int | None,
        birth_info: dict[str, Any],
        calendar_payload: dict[str, Any],
    ) -> None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                INSERT INTO monthly_calendars (
                  user_id, month_key, source_result_id, birth_info_json, calendar_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, month_key) DO UPDATE SET
                  source_result_id = excluded.source_result_id,
                  birth_info_json = excluded.birth_info_json,
                  calendar_json = excluded.calendar_json,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (
                    int(user_id),
                    month_key,
                    int(source_result_id) if source_result_id is not None else None,
                    json.dumps(birth_info, ensure_ascii=False),
                    json.dumps(calendar_payload, ensure_ascii=False),
                ),
            )

    def get_monthly_calendar(self, *, user_id: int, month_key: str) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM monthly_calendars
                WHERE user_id = ? AND month_key = ?
                LIMIT 1
                """,
                (int(user_id), month_key),
            )
            row = cursor.fetchone()
        raw = _row_to_dict(row)
        if not raw:
            return None
        return {
            "month_key": raw.get("month_key"),
            "source_result_id": raw.get("source_result_id"),
            "birth_info": json.loads(raw.get("birth_info_json") or "{}"),
            "calendar": json.loads(raw.get("calendar_json") or "{}"),
            "updated_at": raw.get("updated_at"),
            "created_at": raw.get("created_at"),
        }

    def list_latest_birth_info_by_user(self) -> list[dict[str, Any]]:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                SELECT r.user_id, r.id AS result_id, r.birth_info_json
                FROM analysis_results r
                INNER JOIN (
                  SELECT user_id, MAX(id) AS max_id
                  FROM analysis_results
                  WHERE user_id IS NOT NULL
                  GROUP BY user_id
                ) t ON t.max_id = r.id
                ORDER BY r.user_id ASC
                """
            )
            rows = cursor.fetchall()

        output: list[dict[str, Any]] = []
        for row in rows:
            raw = _row_to_dict(row)
            if not raw:
                continue
            user_id = raw.get("user_id")
            if user_id is None:
                continue
            output.append(
                {
                    "user_id": int(user_id),
                    "result_id": int(raw.get("result_id")),
                    "birth_info": json.loads(raw.get("birth_info_json") or "{}"),
                }
            )
        return output

    def get_result_birth_info(
        self,
        *,
        result_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            if is_admin or user_id is None:
                cursor.execute(
                    """
                    SELECT user_id, birth_info_json
                    FROM analysis_results
                    WHERE id = ?
                    LIMIT 1
                    """,
                    (int(result_id),),
                )
            else:
                cursor.execute(
                    """
                    SELECT user_id, birth_info_json
                    FROM analysis_results
                    WHERE id = ? AND user_id = ?
                    LIMIT 1
                    """,
                    (int(result_id), int(user_id)),
                )
            row = cursor.fetchone()

        raw = _row_to_dict(row)
        if not raw:
            return None
        return {
            "user_id": int(raw.get("user_id")) if raw.get("user_id") is not None else None,
            "birth_info": json.loads(raw.get("birth_info_json") or "{}"),
        }

    def claim_scheduler_run(self, *, job_name: str, run_key: str) -> bool:
        try:
            with db_cursor(self.database_path) as cursor:
                cursor.execute(
                    """
                    INSERT INTO scheduler_runs (job_name, run_key)
                    VALUES (?, ?)
                    """,
                    (job_name, run_key),
                )
            return True
        except sqlite3.IntegrityError:
            return False
