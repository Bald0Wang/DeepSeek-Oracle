import time
from datetime import date

from app import create_app
from app.services import get_insight_service


def _run_once(app) -> None:
    with app.app_context():
        today = date.today()
        precompute_day = int(app.config.get("CALENDAR_PRECOMPUTE_DAY", 15))
        if today.day != precompute_day:
            app.logger.info(
                "scheduler idle: today=%s precompute_day=%s",
                today.isoformat(),
                precompute_day,
            )
            return

        result = get_insight_service().precompute_next_month_for_all_users(target_day=today)
        app.logger.info("scheduler run result=%s", result)


def main() -> None:
    app = create_app()
    poll_seconds = max(60, int(app.config.get("SCHEDULER_POLL_SECONDS", 3600)))
    app.logger.info("insight scheduler started, poll_seconds=%s", poll_seconds)

    while True:
        try:
            _run_once(app)
        except Exception as exc:  # pragma: no cover
            app.logger.exception("scheduler iteration failed: %s", exc)
        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
