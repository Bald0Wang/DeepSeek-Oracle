from __future__ import annotations

from datetime import datetime, timedelta
from flask import current_app

from app.models import SystemLogRepo, UserRepo
from app.models.database import db_cursor


class AdminService:
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.user_repo = UserRepo(database_path)
        self.system_log_repo = SystemLogRepo(database_path)

    def get_dashboard(self, range_key: str = "24h") -> dict:
        """获取管理员大屏数据，支持按时间窗口返回趋势。"""
        normalized_range = self._normalize_range_key(range_key)
        with db_cursor(self.database_path) as cursor:
            # Analysis tasks and result metrics.
            cursor.execute("SELECT COUNT(1) AS total FROM analysis_tasks")
            total_tasks = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COUNT(1) AS total FROM analysis_tasks WHERE status = 'queued'")
            queued_tasks = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COUNT(1) AS total FROM analysis_tasks WHERE status = 'running'")
            running_tasks = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COUNT(1) AS total FROM analysis_tasks WHERE status = 'succeeded'")
            succeeded_tasks = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COUNT(1) AS total FROM analysis_tasks WHERE status = 'failed'")
            failed_tasks = int(cursor.fetchone()["total"])

            cursor.execute("SELECT COUNT(1) AS total FROM analysis_results")
            total_results = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(1) AS total
                FROM analysis_results
                WHERE created_at >= DATETIME('now', '-1 day')
                """
            )
            results_last_24h = int(cursor.fetchone()["total"])

            cursor.execute(
                """
                SELECT COALESCE(SUM(total_token_count), 0) AS total_tokens
                FROM analysis_results
                """
            )
            total_tokens = int(cursor.fetchone()["total_tokens"])
            cursor.execute(
                """
                SELECT COALESCE(SUM(total_token_count), 0) AS total_tokens
                FROM analysis_results
                WHERE created_at >= DATETIME('now', '-1 day')
                """
            )
            tokens_last_24h = int(cursor.fetchone()["total_tokens"])

            # Chat runtime metrics.
            cursor.execute("SELECT COUNT(1) AS total FROM oracle_conversations")
            total_conversations = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COUNT(1) AS total FROM oracle_turns")
            total_chat_turns = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(1) AS total
                FROM oracle_turns
                WHERE created_at >= DATETIME('now', '-1 day')
                """
            )
            chat_turns_last_24h = int(cursor.fetchone()["total"])

            # Divination runtime metrics.
            cursor.execute("SELECT COUNT(1) AS total FROM divination_records WHERE divination_type = 'ziwei'")
            total_ziwei_runs = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COUNT(1) AS total FROM divination_records WHERE divination_type = 'meihua'")
            total_meihua_runs = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(1) AS total
                FROM divination_records
                WHERE divination_type = 'ziwei'
                  AND created_at >= DATETIME('now', '-1 day')
                """
            )
            ziwei_runs_last_24h = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(1) AS total
                FROM divination_records
                WHERE divination_type = 'meihua'
                  AND created_at >= DATETIME('now', '-1 day')
                """
            )
            meihua_runs_last_24h = int(cursor.fetchone()["total"])

            # Insight runtime metrics.
            cursor.execute("SELECT COUNT(1) AS total FROM life_kline_profiles")
            total_kline_profiles = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COUNT(1) AS total FROM monthly_calendars")
            total_calendar_rows = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(1) AS total
                FROM life_kline_profiles
                WHERE updated_at >= DATETIME('now', '-1 day')
                """
            )
            kline_updates_last_24h = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(1) AS total
                FROM monthly_calendars
                WHERE updated_at >= DATETIME('now', '-1 day')
                """
            )
            calendar_updates_last_24h = int(cursor.fetchone()["total"])

            # Auth/token metrics (token is stateless, so use auth log events as token issuance proxy).
            cursor.execute(
                """
                SELECT COUNT(1) AS total
                FROM system_logs
                WHERE created_at >= DATETIME('now', '-1 day')
                  AND path IN ('/api/auth/login', '/api/auth/admin/code-login', '/api/auth/register')
                  AND status_code BETWEEN 200 AND 299
                """
            )
            token_issued_last_24h = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(1) AS total
                FROM system_logs
                WHERE created_at >= DATETIME('now', '-1 day')
                  AND path = '/api/auth/logout'
                  AND status_code BETWEEN 200 AND 299
                """
            )
            token_logout_last_24h = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(1) AS total
                FROM system_logs
                WHERE created_at >= DATETIME('now', '-1 day')
                  AND status_code = 401
                """
            )
            token_invalid_last_24h = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(DISTINCT user_id) AS total
                FROM system_logs
                WHERE created_at >= DATETIME('now', '-1 day')
                  AND user_id IS NOT NULL
                """
            )
            active_users_last_24h = int(cursor.fetchone()["total"])

            # Runtime trend with selected range.
            trend = self._build_runtime_trend(cursor, normalized_range)

        user_metrics = {
            "total_users": self.user_repo.count_users(),
            "admin_users": self.user_repo.count_admins(),
            "active_users_last_24h": active_users_last_24h,
        }
        log_metrics = self.system_log_repo.get_overview_metrics()

        return {
            "user_metrics": user_metrics,
            "token_metrics": {
                "issued_last_24h": token_issued_last_24h,
                "logout_last_24h": token_logout_last_24h,
                "invalid_last_24h": token_invalid_last_24h,
            },
            "analysis_metrics": {
                "total_tasks": total_tasks,
                "queued_tasks": queued_tasks,
                "running_tasks": running_tasks,
                "succeeded_tasks": succeeded_tasks,
                "failed_tasks": failed_tasks,
                "total_results": total_results,
                "results_last_24h": results_last_24h,
                "total_tokens": total_tokens,
                "tokens_last_24h": tokens_last_24h,
            },
            "runtime_metrics": {
                "chat": {
                    "total_conversations": total_conversations,
                    "total_turns": total_chat_turns,
                    "turns_last_24h": chat_turns_last_24h,
                },
                "insight": {
                    "total_kline_profiles": total_kline_profiles,
                    "total_calendars": total_calendar_rows,
                    "kline_updates_last_24h": kline_updates_last_24h,
                    "calendar_updates_last_24h": calendar_updates_last_24h,
                },
                "divination": {
                    "total_ziwei_runs": total_ziwei_runs,
                    "total_meihua_runs": total_meihua_runs,
                    "ziwei_runs_last_24h": ziwei_runs_last_24h,
                    "meihua_runs_last_24h": meihua_runs_last_24h,
                },
            },
            "log_metrics": log_metrics,
            "trend_range": normalized_range,
            "trend": trend,
        }

    def get_logs(self, page: int = 1, page_size: int = 50) -> dict:
        return self.system_log_repo.list_logs(page=page, page_size=page_size)

    def get_users(self, page: int = 1, page_size: int = 20) -> dict:
        return self.user_repo.list_users(page=page, page_size=page_size)

    def _build_runtime_trend(self, cursor, range_key: str) -> list[dict]:
        """构建运行趋势数据，支持 24h / 7d / 30d。"""
        hours, bucket_unit = self._trend_window_config(range_key)
        buckets = self._build_time_buckets(hours=hours, bucket_unit=bucket_unit)
        cutoff_expr = f"-{hours} hours"
        group_expr = "%Y-%m-%d %H:00" if bucket_unit == "hour" else "%Y-%m-%d"

        def fill_from_query(sql: str, key: str, args: tuple = ()) -> None:
            cursor.execute(sql, args)
            for row in cursor.fetchall():
                hour_key = str(row["hour_key"])
                if hour_key in buckets:
                    buckets[hour_key][key] = int(row["total"])

        fill_from_query(
            """
            SELECT strftime(?, created_at) AS hour_key, COUNT(1) AS total
            FROM analysis_tasks
            WHERE created_at >= DATETIME('now', ?)
            GROUP BY strftime(?, created_at)
            """,
            "analysis_tasks",
            (group_expr, cutoff_expr, group_expr),
        )
        fill_from_query(
            """
            SELECT strftime(?, created_at) AS hour_key, COUNT(1) AS total
            FROM oracle_turns
            WHERE created_at >= DATETIME('now', ?)
            GROUP BY strftime(?, created_at)
            """,
            "chat_turns",
            (group_expr, cutoff_expr, group_expr),
        )
        fill_from_query(
            """
            SELECT strftime(?, created_at) AS hour_key, COUNT(1) AS total
            FROM divination_records
            WHERE created_at >= DATETIME('now', ?)
              AND divination_type = 'ziwei'
            GROUP BY strftime(?, created_at)
            """,
            "ziwei_runs",
            (group_expr, cutoff_expr, group_expr),
        )
        fill_from_query(
            """
            SELECT strftime(?, created_at) AS hour_key, COUNT(1) AS total
            FROM divination_records
            WHERE created_at >= DATETIME('now', ?)
              AND divination_type = 'meihua'
            GROUP BY strftime(?, created_at)
            """,
            "meihua_runs",
            (group_expr, cutoff_expr, group_expr),
        )
        fill_from_query(
            """
            SELECT strftime(?, updated_at) AS hour_key, COUNT(1) AS total
            FROM life_kline_profiles
            WHERE updated_at >= DATETIME('now', ?)
            GROUP BY strftime(?, updated_at)
            """,
            "kline_updates",
            (group_expr, cutoff_expr, group_expr),
        )
        fill_from_query(
            """
            SELECT strftime(?, updated_at) AS hour_key, COUNT(1) AS total
            FROM monthly_calendars
            WHERE updated_at >= DATETIME('now', ?)
            GROUP BY strftime(?, updated_at)
            """,
            "calendar_updates",
            (group_expr, cutoff_expr, group_expr),
        )

        return list(buckets.values())

    @staticmethod
    def _normalize_range_key(range_key: str) -> str:
        """规范化趋势范围参数。"""
        return range_key if range_key in {"24h", "7d", "30d"} else "24h"

    @staticmethod
    def _trend_window_config(range_key: str) -> tuple[int, str]:
        """返回趋势窗口小时数和聚合粒度。"""
        if range_key == "7d":
            return 24 * 7, "day"
        if range_key == "30d":
            return 24 * 30, "day"
        return 24, "hour"

    @staticmethod
    def _build_time_buckets(*, hours: int, bucket_unit: str) -> dict[str, dict]:
        """按窗口与粒度构建空桶，便于后续合并各模块统计。"""
        now = datetime.utcnow()
        if bucket_unit == "hour":
            now = now.replace(minute=0, second=0, microsecond=0)
            bucket_count = hours
        else:
            now = now.replace(hour=0, minute=0, second=0, microsecond=0)
            bucket_count = max(1, hours // 24)

        buckets: dict[str, dict] = {}
        for offset in range(bucket_count - 1, -1, -1):
            if bucket_unit == "hour":
                point = now - timedelta(hours=offset)
                key = point.strftime("%Y-%m-%d %H:00")
                label = point.strftime("%H:00")
            else:
                point = now - timedelta(days=offset)
                key = point.strftime("%Y-%m-%d")
                label = point.strftime("%m-%d")
            buckets[key] = {
                "label": label,
                "analysis_tasks": 0,
                "chat_turns": 0,
                "kline_updates": 0,
                "calendar_updates": 0,
                "ziwei_runs": 0,
                "meihua_runs": 0,
            }
        return buckets


def get_admin_service() -> AdminService:
    service = current_app.extensions.get("admin_service")
    if service:
        return service
    service = AdminService(database_path=current_app.config["DATABASE_PATH"])
    current_app.extensions["admin_service"] = service
    return service
