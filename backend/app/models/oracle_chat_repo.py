import json
from typing import Any

from .database import db_cursor


def _row_to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


class OracleChatRepo:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def create_conversation(self, user_id: int, title: str | None = None) -> dict[str, Any]:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                INSERT INTO oracle_conversations (user_id, title, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (int(user_id), (title or "").strip() or None),
            )
            conversation_id = int(cursor.lastrowid or 0)
            cursor.execute(
                """
                SELECT id, user_id, title, created_at, updated_at
                FROM oracle_conversations
                WHERE id = ?
                LIMIT 1
                """,
                (conversation_id,),
            )
            row = cursor.fetchone()
        return _row_to_dict(row) or {
            "id": conversation_id,
            "user_id": int(user_id),
            "title": title,
        }

    def get_conversation(self, user_id: int, conversation_id: int) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                SELECT id, user_id, title, created_at, updated_at
                FROM oracle_conversations
                WHERE id = ? AND user_id = ?
                LIMIT 1
                """,
                (int(conversation_id), int(user_id)),
            )
            row = cursor.fetchone()
        return _row_to_dict(row)

    def touch_conversation(self, conversation_id: int, title: str | None = None) -> None:
        if title and title.strip():
            with db_cursor(self.database_path) as cursor:
                cursor.execute(
                    """
                    UPDATE oracle_conversations
                    SET title = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (title.strip(), int(conversation_id)),
                )
            return

        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                UPDATE oracle_conversations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (int(conversation_id),),
            )

    def list_conversations(self, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = min(max(int(limit), 1), 100)
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                SELECT
                  c.id,
                  c.title,
                  c.created_at,
                  c.updated_at,
                  (
                    SELECT COUNT(1)
                    FROM oracle_turns t_count
                    WHERE t_count.conversation_id = c.id
                  ) AS turn_count,
                  (
                    SELECT t_last.user_query
                    FROM oracle_turns t_last
                    WHERE t_last.conversation_id = c.id
                    ORDER BY t_last.id DESC
                    LIMIT 1
                  ) AS last_query
                FROM oracle_conversations c
                WHERE c.user_id = ?
                ORDER BY c.updated_at DESC, c.id DESC
                LIMIT ?
                """,
                (int(user_id), safe_limit),
            )
            rows = cursor.fetchall()
        return [_row_to_dict(row) or {} for row in rows]

    def append_turn(
        self,
        conversation_id: int,
        *,
        user_query: str,
        context_summary: str,
        status: str,
        plan_steps: list[dict[str, Any]],
        answer_text: str,
        action_items: list[dict[str, Any]],
        follow_up_questions: list[str],
        safety_disclaimer_level: str,
        error_message: str | None,
    ) -> dict[str, Any]:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                INSERT INTO oracle_turns (
                  conversation_id,
                  user_query,
                  context_summary,
                  status,
                  plan_steps_json,
                  answer_text,
                  action_items_json,
                  follow_up_questions_json,
                  safety_disclaimer_level,
                  error_message,
                  updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    int(conversation_id),
                    user_query.strip(),
                    context_summary.strip(),
                    status,
                    json.dumps(plan_steps, ensure_ascii=False),
                    answer_text,
                    json.dumps(action_items, ensure_ascii=False),
                    json.dumps(follow_up_questions, ensure_ascii=False),
                    safety_disclaimer_level,
                    error_message,
                ),
            )
            turn_id = int(cursor.lastrowid or 0)
        self.touch_conversation(conversation_id)
        return self.get_turn_by_id(conversation_id, turn_id) or {"id": turn_id}

    def get_turn_by_id(self, conversation_id: int, turn_id: int) -> dict[str, Any] | None:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM oracle_turns
                WHERE id = ? AND conversation_id = ?
                LIMIT 1
                """,
                (int(turn_id), int(conversation_id)),
            )
            row = cursor.fetchone()
        return self._normalize_turn_row(row)

    def list_turns(self, user_id: int, conversation_id: int) -> list[dict[str, Any]]:
        with db_cursor(self.database_path) as cursor:
            cursor.execute(
                """
                SELECT c.id
                FROM oracle_conversations c
                WHERE c.id = ? AND c.user_id = ?
                LIMIT 1
                """,
                (int(conversation_id), int(user_id)),
            )
            exists = cursor.fetchone()
            if not exists:
                return []
            cursor.execute(
                """
                SELECT *
                FROM oracle_turns
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (int(conversation_id),),
            )
            rows = cursor.fetchall()
        return [self._normalize_turn_row(row) for row in rows if row is not None]

    def _normalize_turn_row(self, row) -> dict[str, Any] | None:
        raw = _row_to_dict(row)
        if raw is None:
            return None
        try:
            plan_steps = json.loads(raw.get("plan_steps_json") or "[]")
            action_items = json.loads(raw.get("action_items_json") or "[]")
            follow_up_questions = json.loads(raw.get("follow_up_questions_json") or "[]")
        except json.JSONDecodeError:
            plan_steps = []
            action_items = []
            follow_up_questions = []
        return {
            "id": raw["id"],
            "conversation_id": raw["conversation_id"],
            "user_query": raw["user_query"],
            "context_summary": raw["context_summary"],
            "status": raw["status"],
            "plan_steps": plan_steps if isinstance(plan_steps, list) else [],
            "answer_text": raw["answer_text"] or "",
            "action_items": action_items if isinstance(action_items, list) else [],
            "follow_up_questions": follow_up_questions if isinstance(follow_up_questions, list) else [],
            "safety_disclaimer_level": raw["safety_disclaimer_level"] or "none",
            "error_message": raw.get("error_message"),
            "created_at": raw["created_at"],
            "updated_at": raw["updated_at"],
        }
