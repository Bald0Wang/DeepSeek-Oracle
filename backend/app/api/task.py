from flask import Blueprint

from app.services import get_analysis_service
from app.utils.auth import require_auth
from app.utils.response import success_response


task_bp = Blueprint("task", __name__)


@task_bp.get("/task/<task_id>")
@require_auth()
def get_task(task_id: str):
    service = get_analysis_service()
    data = service.get_task(task_id)
    return success_response(data=data)


@task_bp.post("/task/<task_id>/cancel")
@require_auth()
def cancel_task(task_id: str):
    service = get_analysis_service()
    data = service.cancel_task(task_id)
    return success_response(data=data)


@task_bp.post("/task/<task_id>/retry")
@require_auth()
def retry_task(task_id: str):
    service = get_analysis_service()
    data = service.retry_task(task_id)
    return success_response(data=data)
