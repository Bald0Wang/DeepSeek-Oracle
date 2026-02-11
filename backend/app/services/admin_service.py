from __future__ import annotations

from flask import current_app

from app.models import SystemLogRepo, UserRepo
from app.models.database import db_cursor


class AdminService:
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.user_repo = UserRepo(database_path)
        self.system_log_repo = SystemLogRepo(database_path)

    def get_dashboard(self) -> dict:
        with db_cursor(self.database_path) as cursor:
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

        user_metrics = {
            "total_users": self.user_repo.count_users(),
            "admin_users": self.user_repo.count_admins(),
        }
        log_metrics = self.system_log_repo.get_overview_metrics()

        return {
            "user_metrics": user_metrics,
            "analysis_metrics": {
                "total_tasks": total_tasks,
                "queued_tasks": queued_tasks,
                "running_tasks": running_tasks,
                "succeeded_tasks": succeeded_tasks,
                "failed_tasks": failed_tasks,
                "total_results": total_results,
                "results_last_24h": results_last_24h,
            },
            "log_metrics": log_metrics,
        }

    def get_logs(self, page: int = 1, page_size: int = 50) -> dict:
        return self.system_log_repo.list_logs(page=page, page_size=page_size)

    def get_users(self, page: int = 1, page_size: int = 20) -> dict:
        return self.user_repo.list_users(page=page, page_size=page_size)


def get_admin_service() -> AdminService:
    service = current_app.extensions.get("admin_service")
    if service:
        return service
    service = AdminService(database_path=current_app.config["DATABASE_PATH"])
    current_app.extensions["admin_service"] = service
    return service
