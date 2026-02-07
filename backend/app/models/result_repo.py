import json
import sqlite3
from typing import Any

from .database import db_cursor


def _row_to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


class ResultRepo:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def find_by_cache_key(self, cache_key: str) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                "SELECT id, created_at FROM analysis_results WHERE cache_key = ? LIMIT 1",
                (cache_key,),
            )
            row = cursor.fetchone()
        return _row_to_dict(row)

    def save_result(
        self,
        cache_key: str,
        birth_info: dict[str, Any],
        text_description: str,
        provider: str,
        model: str,
        prompt_version: str,
        analysis: dict[str, dict[str, Any]],
        total_execution_time: float,
        total_token_count: int,
    ) -> int:
        try:
            with db_cursor(self.database_path) as cursor:
                cursor.execute(
                    """
                    INSERT INTO analysis_results (
                      cache_key,
                      birth_info_json,
                      text_description,
                      provider,
                      model,
                      prompt_version,
                      total_execution_time,
                      total_token_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cache_key,
                        json.dumps(birth_info, ensure_ascii=False),
                        text_description,
                        provider,
                        model,
                        prompt_version,
                        total_execution_time,
                        total_token_count,
                    ),
                )
                if cursor.lastrowid is None:
                    raise RuntimeError("insert result failed")
                result_id = int(cursor.lastrowid)

                for analysis_type, item in analysis.items():
                    cursor.execute(
                        """
                        INSERT INTO analysis_items (
                          result_id,
                          analysis_type,
                          content,
                          execution_time,
                          input_tokens,
                          output_tokens,
                          token_count
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            result_id,
                            analysis_type,
                            item["content"],
                            float(item["execution_time"]),
                            int(item["input_tokens"]),
                            int(item["output_tokens"]),
                            int(item["token_count"]),
                        ),
                    )

            return result_id
        except sqlite3.IntegrityError:
            cached = self.find_by_cache_key(cache_key)
            if cached:
                return int(cached["id"])
            raise

    def get_result(self, result_id: int) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                "SELECT * FROM analysis_results WHERE id = ? LIMIT 1",
                (result_id,),
            )
            result_row = cursor.fetchone()
            if not result_row:
                return None

            cursor.execute(
                "SELECT * FROM analysis_items WHERE result_id = ? ORDER BY id ASC",
                (result_id,),
            )
            item_rows = cursor.fetchall()

        result = _row_to_dict(result_row)
        if result is None:
            return None
        birth_info = json.loads(result["birth_info_json"])

        analysis_payload: dict[str, Any] = {}
        for row in item_rows:
            item = _row_to_dict(row)
            if item is None:
                continue
            analysis_payload[item["analysis_type"]] = {
                "content": item["content"],
                "execution_time": item["execution_time"],
                "token_count": item["token_count"],
                "input_tokens": item["input_tokens"],
                "output_tokens": item["output_tokens"],
            }

        return {
            "id": result["id"],
            "birth_info": birth_info,
            "provider": result["provider"],
            "model": result["model"],
            "prompt_version": result["prompt_version"],
            "text_description": result["text_description"],
            "analysis": analysis_payload,
            "total_execution_time": result["total_execution_time"],
            "total_token_count": result["total_token_count"],
            "created_at": result["created_at"],
        }

    def get_history(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        offset = (page - 1) * page_size

        with db_cursor(self.database_path) as cursor:
            cursor.execute("SELECT COUNT(1) AS total FROM analysis_results")
            total = int(cursor.fetchone()["total"])

            cursor.execute(
                """
                SELECT id, birth_info_json, provider, model, prompt_version, created_at
                FROM analysis_results
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (page_size, offset),
            )
            rows = cursor.fetchall()

        items = []
        for row in rows:
            raw = _row_to_dict(row)
            if raw is None:
                continue
            birth_info = json.loads(raw["birth_info_json"])
            items.append(
                {
                    "id": raw["id"],
                    "date": birth_info.get("date"),
                    "timezone": birth_info.get("timezone"),
                    "gender": birth_info.get("gender"),
                    "calendar": birth_info.get("calendar"),
                    "provider": raw["provider"],
                    "model": raw["model"],
                    "prompt_version": raw["prompt_version"],
                    "created_at": raw["created_at"],
                }
            )

        return {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "has_next": offset + page_size < total,
            },
        }

    def get_result_item(self, result_id: int, analysis_type: str) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                SELECT
                  r.id AS result_id,
                  r.provider,
                  r.model,
                  r.prompt_version,
                  r.created_at,
                  i.analysis_type,
                  i.content,
                  i.execution_time,
                  i.input_tokens,
                  i.output_tokens,
                  i.token_count
                FROM analysis_results r
                INNER JOIN analysis_items i ON i.result_id = r.id
                WHERE r.id = ? AND i.analysis_type = ?
                LIMIT 1
                """,
                (result_id, analysis_type),
            )
            row = cursor.fetchone()

        item = _row_to_dict(row)
        if item is None:
            return None

        return {
            "result_id": item["result_id"],
            "analysis_type": item["analysis_type"],
            "content": item["content"],
            "execution_time": item["execution_time"],
            "input_tokens": item["input_tokens"],
            "output_tokens": item["output_tokens"],
            "token_count": item["token_count"],
            "provider": item["provider"],
            "model": item["model"],
            "prompt_version": item["prompt_version"],
            "created_at": item["created_at"],
        }

    def render_markdown(self, result: dict[str, Any], scope: str = "full") -> str:
        title_map = {
            "marriage_path": "婚姻道路分析",
            "challenges": "困难挑战分析",
            "partner_character": "伴侣性格分析",
        }

        birth_info = result["birth_info"]
        lines = ["# 紫微斗数分析报告", "", "## 基本信息"]
        lines.append(f"- 日期: {birth_info.get('date', '')}")
        lines.append(f"- 时辰: {birth_info.get('timezone', '')}")
        lines.append(f"- 性别: {birth_info.get('gender', '')}")
        lines.append(f"- 历法: {birth_info.get('calendar', '')}")
        lines.append(f"- Provider: {result.get('provider', '')}")
        lines.append(f"- Model: {result.get('model', '')}")
        lines.append(f"- Prompt Version: {result.get('prompt_version', '')}")
        lines.append("")
        lines.append("## 命盘描述")
        lines.append(result.get("text_description", ""))
        lines.append("")

        analysis = result.get("analysis", {})
        for analysis_type, item in analysis.items():
            if scope != "full" and scope != analysis_type:
                continue

            lines.append(f"## {title_map.get(analysis_type, analysis_type)}")
            lines.append(f"- 推理耗时: {item.get('execution_time', 0)} 秒")
            lines.append(f"- Token 数量: {item.get('token_count', 0)}")
            lines.append("")
            lines.append(item.get("content", ""))
            lines.append("")

        return "\n".join(lines)
