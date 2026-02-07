import hashlib
import tempfile
import uuid
from pathlib import Path
from typing import Any

from flask import current_app

from app.models import ResultRepo, TaskRepo
from app.services.llm_service import LLMService
from app.services.ziwei_service import ZiweiService
from app.utils.errors import AppError, business_error


class CancelledTaskError(Exception):
    pass


class AnalysisService:
    def __init__(
        self,
        database_path: str,
        queue,
        iztro_base_url: str,
        default_provider: str,
        default_model: str,
        default_prompt_version: str,
        request_timeout_s: int,
        max_task_retry: int,
        llm_max_retries: int,
    ):
        self.task_repo = TaskRepo(database_path)
        self.result_repo = ResultRepo(database_path)
        self.queue = queue
        self.ziwei_service = ZiweiService(iztro_base_url)
        self.default_provider = default_provider
        self.default_model = default_model
        self.default_prompt_version = default_prompt_version
        self.request_timeout_s = request_timeout_s
        self.max_task_retry = max_task_retry
        self.llm_max_retries = llm_max_retries

    def submit_analysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        provider = payload.get("provider", self.default_provider)
        model = payload.get("model", self.default_model)
        prompt_version = payload.get("prompt_version", self.default_prompt_version)

        birth_info = {
            "date": payload["date"],
            "timezone": int(payload["timezone"]),
            "gender": payload["gender"],
            "calendar": payload["calendar"],
        }

        cache_key = self._build_cache_key(
            date=birth_info["date"],
            timezone=birth_info["timezone"],
            gender=birth_info["gender"],
            calendar=birth_info["calendar"],
            provider=provider,
            model=model,
            prompt_version=prompt_version,
        )

        cached = self.result_repo.find_by_cache_key(cache_key)
        if cached:
            return {
                "hit_cache": True,
                "result_id": int(cached["id"]),
            }

        active_task = self.task_repo.find_active_task_by_cache_key(cache_key)
        if active_task:
            return {
                "hit_cache": False,
                "task_id": active_task["task_id"],
                "status": active_task["status"],
                "poll_after_ms": 2000,
                "reused_task": True,
            }

        task_id = f"task_{uuid.uuid4().hex[:16]}"
        self.task_repo.create_task(
            task_id=task_id,
            birth_info=birth_info,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            cache_key=cache_key,
        )

        self._enqueue_task(task_id)

        return {
            "hit_cache": False,
            "task_id": task_id,
            "status": "queued",
            "poll_after_ms": 2000,
        }

    def get_task(self, task_id: str) -> dict[str, Any]:
        task = self.task_repo.get_task(task_id)
        if not task:
            raise business_error("A4004", "task not found", 404, False)

        error_payload = None
        if task.get("error_code"):
            retryable = task.get("error_code") in {"A2001", "A3001", "A3002", "A4290"}
            error_payload = {
                "code": task.get("error_code"),
                "message": task.get("error_message"),
                "retryable": retryable,
            }

        return {
            "task_id": task["task_id"],
            "status": task["status"],
            "progress": task["progress"],
            "step": task.get("step") or "",
            "result_id": task.get("result_id"),
            "error": error_payload,
            "retry_count": task.get("retry_count", 0),
            "updated_at": task.get("finished_at") or task.get("started_at") or task.get("created_at"),
        }

    def cancel_task(self, task_id: str) -> dict[str, Any]:
        task = self.task_repo.get_task(task_id)
        if not task:
            raise business_error("A4004", "task not found", 404, False)

        if task["status"] not in {"queued", "running"}:
            raise business_error("A4009", "task cannot be cancelled in current status", 409, False)

        self.task_repo.mark_cancelled(task_id)
        return {"task_id": task_id, "status": "cancelled"}

    def retry_task(self, task_id: str) -> dict[str, Any]:
        task = self.task_repo.get_task(task_id)
        if not task:
            raise business_error("A4004", "task not found", 404, False)

        if task["status"] != "failed":
            raise business_error("A4009", "only failed task can retry", 409, False)

        retry_count = self.task_repo.increment_retry(task_id)
        if retry_count > self.max_task_retry:
            raise business_error("A4009", "max retry reached", 409, False)

        self.task_repo.set_queued(task_id)
        self._enqueue_task(task_id)
        return {"task_id": task_id, "status": "queued", "retry_count": retry_count}

    def get_result(self, result_id: int) -> dict[str, Any]:
        result = self.result_repo.get_result(result_id)
        if not result:
            raise business_error("A4004", "result not found", 404, False)
        return result

    def get_result_item(self, result_id: int, analysis_type: str) -> dict[str, Any]:
        if analysis_type not in {"marriage_path", "challenges", "partner_character"}:
            raise business_error("A1002", "invalid analysis type", 422, False)

        item = self.result_repo.get_result_item(result_id, analysis_type)
        if not item:
            raise business_error("A4004", "analysis item not found", 404, False)
        return item

    def get_history(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        return self.result_repo.get_history(page=page, page_size=page_size)

    def check_cache(self, payload: dict[str, Any]) -> dict[str, Any]:
        provider = payload.get("provider", self.default_provider)
        model = payload.get("model", self.default_model)
        prompt_version = payload.get("prompt_version", self.default_prompt_version)

        cache_key = self._build_cache_key(
            date=payload["date"],
            timezone=int(payload["timezone"]),
            gender=payload["gender"],
            calendar=payload["calendar"],
            provider=provider,
            model=model,
            prompt_version=prompt_version,
        )

        cached = self.result_repo.find_by_cache_key(cache_key)
        if not cached:
            return {"cached_results": None, "result_id": None}

        result = self.result_repo.get_result(int(cached["id"]))
        if not result:
            return {"cached_results": None, "result_id": None}

        cached_results: dict[str, str] = {}
        for analysis_type, item in result.get("analysis", {}).items():
            cached_results[analysis_type] = (
                f"推理耗时: {item.get('execution_time', 0)}秒\n"
                f"Token 数量: {item.get('token_count', 0)}\n\n"
                f"{item.get('content', '')}"
            )

        return {
            "cached_results": cached_results if cached_results else None,
            "result_id": result["id"],
        }

    def export_markdown_file(self, result_id: int, scope: str = "full") -> Path:
        result = self.get_result(result_id)
        content = self.result_repo.render_markdown(result=result, scope=scope)

        tmp_dir = Path(tempfile.gettempdir())
        filename = tmp_dir / f"analysis_{result_id}_{scope}.md"
        filename.write_text(content, encoding="utf-8")
        return filename

    def run_task(self, task_id: str) -> None:
        task = self.task_repo.get_task(task_id)
        if not task:
            return

        try:
            self._raise_if_cancelled(task_id)
            self.task_repo.mark_running(task_id, step="generate_chart", progress=15)

            birth_info = {
                "date": task["birth_date"],
                "timezone": task["timezone"],
                "gender": task["gender"],
                "calendar": task["calendar"],
            }

            astrolabe_data = self.ziwei_service.get_astrolabe_data(**birth_info)
            text_description = self.ziwei_service.build_text_description(astrolabe_data)

            self._raise_if_cancelled(task_id)
            self.task_repo.mark_progress(task_id, step="llm_batch", progress=80)

            llm_service = LLMService(
                provider_name=task["provider"],
                model=task["model"],
                timeout_s=self.request_timeout_s,
                max_retries=self.llm_max_retries,
            )

            def on_llm_progress(step: str, progress: int) -> None:
                self._raise_if_cancelled(task_id)
                self.task_repo.mark_progress(task_id, step=step, progress=progress)

            llm_output = llm_service.analyze_all(
                text_description,
                progress_callback=on_llm_progress,
            )

            self._raise_if_cancelled(task_id)
            self.task_repo.mark_progress(task_id, step="persist_result", progress=95)

            result_id = self.result_repo.save_result(
                cache_key=task["cache_key"],
                birth_info=birth_info,
                text_description=text_description,
                provider=task["provider"],
                model=task["model"],
                prompt_version=task["prompt_version"],
                analysis=llm_output["analysis"],
                total_execution_time=llm_output["total_execution_time"],
                total_token_count=llm_output["total_token_count"],
            )
            self.task_repo.mark_succeeded(task_id, result_id)
        except CancelledTaskError:
            self.task_repo.mark_cancelled(task_id)
        except AppError as exc:
            self.task_repo.mark_failed(task_id, exc.code, exc.message)
            raise
        except Exception as exc:  # pragma: no cover
            self.task_repo.mark_failed(task_id, "A5000", str(exc))
            raise

    def _enqueue_task(self, task_id: str) -> None:
        try:
            self.queue.enqueue(
                "app.workers.analysis_worker.run_analysis_task",
                task_id,
                job_timeout=self.request_timeout_s,
            )
        except Exception as exc:
            raise business_error("A5000", f"enqueue task failed: {exc}", 500, True) from exc

    def _raise_if_cancelled(self, task_id: str) -> None:
        task = self.task_repo.get_task(task_id)
        if not task:
            raise business_error("A4004", "task not found", 404, False)
        if task["status"] == "cancelled":
            raise CancelledTaskError

    @staticmethod
    def _build_cache_key(
        *,
        date: str,
        timezone: int,
        gender: str,
        calendar: str,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> str:
        plain = f"{date}|{timezone}|{gender}|{calendar}|{provider}|{model}|{prompt_version}"
        return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def get_analysis_service() -> AnalysisService:
    service = current_app.extensions.get("analysis_service")
    if service:
        return service

    service = AnalysisService(
        database_path=current_app.config["DATABASE_PATH"],
        queue=current_app.extensions["analysis_queue"],
        iztro_base_url=current_app.config["IZTRO_BASE_URL"],
        default_provider=current_app.config["LLM_PROVIDER"],
        default_model=current_app.config["LLM_MODEL"],
        default_prompt_version=current_app.config["PROMPT_VERSION"],
        request_timeout_s=current_app.config["REQUEST_TIMEOUT_S"],
        max_task_retry=current_app.config["MAX_TASK_RETRY"],
        llm_max_retries=current_app.config["LLM_MAX_RETRIES"],
    )
    current_app.extensions["analysis_service"] = service
    return service
