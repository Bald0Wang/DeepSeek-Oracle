from redis import Redis
from rq import Worker

from app import create_app


def main() -> None:
    app = create_app()
    redis_conn = Redis.from_url(app.config["REDIS_URL"])
    queue_name = app.config["ANALYSIS_QUEUE"]

    worker = Worker([queue_name], connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    main()
