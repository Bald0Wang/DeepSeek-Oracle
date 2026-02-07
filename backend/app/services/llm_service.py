import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from app.llm_providers import create_provider
from app.utils.errors import AppError, business_error


PROMPT_TEMPLATES = {
    "marriage_path": "参考紫微斗数思路对命主婚姻道路进行分析，命盘如下:\n{chart}",
    "challenges": "参考紫微斗数思路对命主与另一半的困难和挑战进行分析，命盘如下:\n{chart}",
    "partner_character": "参考紫微斗数思路对命主另一半的性格和人品进行分析，命盘如下:\n{chart}",
}


class LLMService:
    def __init__(
        self,
        provider_name: str,
        model: str,
        timeout_s: int = 1800,
        max_retries: int = 2,
    ):
        self.provider_name = provider_name
        self.model = model
        self.timeout_s = timeout_s
        self.max_retries = max_retries

    def _analyze_single(self, analysis_type: str, text_description: str) -> dict[str, Any]:
        if analysis_type not in PROMPT_TEMPLATES:
            raise business_error("A1002", f"unknown analysis type: {analysis_type}", 422, False)

        prompt = PROMPT_TEMPLATES[analysis_type].format(chart=text_description)

        response = None
        for attempt in range(self.max_retries + 1):
            try:
                provider = create_provider(self.provider_name, self.model)
                response = provider.generate(prompt, timeout_s=self.timeout_s)
                break
            except AppError as exc:
                if exc.retryable and attempt < self.max_retries:
                    time.sleep(2**attempt)
                    continue
                raise
            except TimeoutError as exc:
                if attempt < self.max_retries:
                    time.sleep(2**attempt)
                    continue
                raise business_error("A3001", f"llm timeout: {exc}", 504, True) from exc
            except Exception as exc:  # pragma: no cover
                if attempt < self.max_retries:
                    time.sleep(2**attempt)
                    continue
                raise business_error("A3002", f"llm provider error: {exc}", 502, True) from exc

        if response is None:
            raise business_error("A3002", "llm provider returned empty response", 502, True)
        assert response is not None

        return {
            "content": response.content,
            "execution_time": round(response.latency_ms / 1000, 2),
            "input_tokens": int(response.usage.input_tokens),
            "output_tokens": int(response.usage.output_tokens),
            "token_count": int(response.usage.total_tokens),
            "provider": response.provider,
            "model": response.model,
        }

    def analyze_all(
        self,
        text_description: str,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> dict[str, Any]:
        analysis_types = ["marriage_path", "challenges", "partner_character"]
        output: dict[str, Any] = {}

        total_start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_map = {
                executor.submit(self._analyze_single, analysis_type, text_description): analysis_type
                for analysis_type in analysis_types
            }

            done_count = 0
            for future in as_completed(future_map):
                analysis_type = future_map[future]
                output[analysis_type] = future.result()
                done_count += 1
                if progress_callback:
                    progress = {1: 45, 2: 65, 3: 85}.get(done_count, 85)
                    progress_callback(f"llm_{analysis_type}", progress)

        total_execution_time = round(time.perf_counter() - total_start, 2)
        total_token_count = sum(item["token_count"] for item in output.values())

        return {
            "analysis": output,
            "total_execution_time": total_execution_time,
            "total_token_count": total_token_count,
        }
