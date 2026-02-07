from app import create_app
from app.services.analysis_service import get_analysis_service


def run_analysis_task(task_id: str) -> None:
    app = create_app()
    with app.app_context():
        service = get_analysis_service()
        service.run_task(task_id)
