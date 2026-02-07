from typing import Any

from .database import db_cursor


def _row_to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


class TaskRepo:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def create_task(
        self,
        task_id: str,
        birth_info: dict[str, Any],
        provider: str,
        model: str,
        prompt_version: str,
        cache_key: str,
    ) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                INSERT INTO analysis_tasks (
                  task_id, status, progress, step,
                  birth_date, timezone, gender, calendar,
                  provider, model, prompt_version, cache_key
                ) VALUES (?, 'queued', 0, 'queued', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    birth_info["date"],
                    int(birth_info["timezone"]),
                    birth_info["gender"],
                    birth_info["calendar"],
                    provider,
                    model,
                    prompt_version,
                    cache_key,
                ),
            )
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                "SELECT * FROM analysis_tasks WHERE task_id = ? LIMIT 1", (task_id,)
            )
            row = cursor.fetchone()
        return _row_to_dict(row)

    def find_active_task_by_cache_key(self, cache_key: str) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM analysis_tasks
                WHERE cache_key = ?
                  AND status IN ('queued', 'running')
                ORDER BY id DESC
                LIMIT 1
                """,
                (cache_key,),
            )
            row = cursor.fetchone()
        return _row_to_dict(row)

    def mark_running(self, task_id: str, step: str, progress: int) -> None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                UPDATE analysis_tasks
                SET status = 'running',
                    step = ?,
                    progress = ?,
                    started_at = COALESCE(started_at, CURRENT_TIMESTAMP),
                    error_code = NULL,
                    error_message = NULL
                WHERE task_id = ?
                """,
                (step, progress, task_id),
            )

    def mark_progress(self, task_id: str, step: str, progress: int) -> None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                UPDATE analysis_tasks
                SET step = ?, progress = ?
                WHERE task_id = ?
                """,
                (step, progress, task_id),
            )

    def mark_succeeded(self, task_id: str, result_id: int) -> None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                UPDATE analysis_tasks
                SET status = 'succeeded',
                    step = 'done',
                    progress = 100,
                    result_id = ?,
                    finished_at = CURRENT_TIMESTAMP,
                    error_code = NULL,
                    error_message = NULL
                WHERE task_id = ?
                """,
                (result_id, task_id),
            )

    def mark_failed(
        self,
        task_id: str,
        error_code: str,
        error_message: str,
        retry_count: int | None = None,
    ) -> None:
        if retry_count is None:
            with db_cursor(self.database_path) as cursor:
                cursor.execute(
                    """
                    UPDATE analysis_tasks
                    SET status = 'failed',
                        error_code = ?,
                        error_message = ?,
                        finished_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                    """,
                    (error_code, error_message, task_id),
                )
            return

        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                UPDATE analysis_tasks
                SET status = 'failed',
                    error_code = ?,
                    error_message = ?,
                    retry_count = ?,
                    finished_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
                """,
                (error_code, error_message, retry_count, task_id),
            )

    def mark_cancelled(self, task_id: str) -> None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                UPDATE analysis_tasks
                SET status = 'cancelled',
                    finished_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
                """,
                (task_id,),
            )

    def increment_retry(self, task_id: str) -> int:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                "UPDATE analysis_tasks SET retry_count = retry_count + 1 WHERE task_id = ?",
                (task_id,),
            )
            cursor.execute(
                "SELECT retry_count FROM analysis_tasks WHERE task_id = ? LIMIT 1", (task_id,)
            )
            row = cursor.fetchone()
        return int(row["retry_count"]) if row else 0

    def set_queued(self, task_id: str, step: str = "queued") -> None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                UPDATE analysis_tasks
                SET status = 'queued',
                    step = ?,
                    progress = 0,
                    finished_at = NULL,
                    error_code = NULL,
                    error_message = NULL
                WHERE task_id = ?
                """,
                (step, task_id),
            )
