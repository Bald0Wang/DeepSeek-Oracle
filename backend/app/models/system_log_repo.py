from __future__ import annotations

from typing import Any

from .database import db_cursor


def _row_to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


class SystemLogRepo:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def create_log(
        self,
        *,
        request_id: str | None,
        method: str | None,
        path: str | None,
        status_code: int | None,
        duration_ms: int | None,
        level: str = "info",
        message: str = "",
        user_id: int | None = None,
        user_email: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                INSERT INTO system_logs (
                  request_id, method, path, status_code, duration_ms,
                  level, message, user_id, user_email, ip, user_agent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    method,
                    path,
                    status_code,
                    duration_ms,
                    level,
                    message,
                    user_id,
                    user_email,
                    ip,
                    user_agent,
                ),
            )

    def list_logs(self, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 200)
        offset = (page - 1) * page_size

        with db_cursor(self.database_path) as cursor:
            cursor.execute("SELECT COUNT(1) AS total FROM system_logs")
            total = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT id, request_id, method, path, status_code, duration_ms, level, message,
                       user_id, user_email, ip, user_agent, created_at
                FROM system_logs
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (page_size, offset),
            )
            rows = cursor.fetchall()

        items = [_row_to_dict(row) for row in rows if row is not None]
        return {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "has_next": offset + page_size < total,
            },
        }

    def get_overview_metrics(self) -> dict[str, Any]:
        with db_cursor(self.database_path) as cursor:
            cursor.execute("SELECT COUNT(1) AS total FROM system_logs")
            total_logs = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COUNT(1) AS total FROM system_logs WHERE status_code >= 500")
            error_logs = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(1) AS total
                FROM system_logs
                WHERE created_at >= DATETIME('now', '-1 day')
                """
            )
            logs_last_24h = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT path, COUNT(1) AS total
                FROM system_logs
                WHERE path IS NOT NULL AND path != ''
                GROUP BY path
                ORDER BY total DESC
                LIMIT 5
                """
            )
            top_paths = [_row_to_dict(row) for row in cursor.fetchall() if row is not None]

        return {
            "total_logs": total_logs,
            "error_logs": error_logs,
            "logs_last_24h": logs_last_24h,
            "top_paths": top_paths,
        }
