import argparse
import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCHEMA_FILE = BACKEND_DIR / "migrations" / "0001_init.sql"


TIME_PATTERN = re.compile(r"推理耗时:\s*([0-9]+(?:\.[0-9]+)?)")
TOKEN_PATTERN = re.compile(r"Token 数量:\s*(\d+)")


def parse_legacy_item(raw_text: str) -> dict[str, Any]:
    if not raw_text:
        return {
            "content": "",
            "execution_time": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "token_count": 0,
        }

    lines = raw_text.splitlines()
    execution_time = 0.0
    token_count = 0
    content_start = 0

    if lines:
        match = TIME_PATTERN.search(lines[0])
        if match:
            execution_time = float(match.group(1))
            content_start = 1

    if len(lines) > 1:
        match = TOKEN_PATTERN.search(lines[1])
        if match:
            token_count = int(match.group(1))
            content_start = 2

    content = "\n".join(lines[content_start:]).strip()
    if not content:
        content = raw_text.strip()

    return {
        "content": content,
        "execution_time": execution_time,
        "input_tokens": 0,
        "output_tokens": token_count,
        "token_count": token_count,
    }


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (table_name,),
    )
    return cursor.fetchone() is not None


def init_new_db(new_db: Path) -> None:
    new_db.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
    conn = sqlite3.connect(str(new_db))
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


def migrate_legacy_results(legacy_db: Path, new_db: Path) -> tuple[int, int]:
    if not legacy_db.exists():
        raise FileNotFoundError(f"legacy db not found: {legacy_db}")

    init_new_db(new_db)

    legacy_conn = sqlite3.connect(str(legacy_db))
    legacy_conn.row_factory = sqlite3.Row
    new_conn = sqlite3.connect(str(new_db))
    new_conn.row_factory = sqlite3.Row

    try:
        if not table_exists(legacy_conn, "results"):
            return 0, 0

        legacy_cursor = legacy_conn.cursor()
        legacy_cursor.execute(
            """
            SELECT id, analysis_type, data, date, timezone, gender, calendar, timestamp
            FROM results
            ORDER BY timestamp ASC, id ASC
            """
        )
        rows = legacy_cursor.fetchall()

        grouped: dict[tuple[str, str, str, str, str], dict[str, Any]] = defaultdict(
            lambda: {"analysis": {}, "max_id": 0}
        )

        for row in rows:
            key = (
                str(row["date"]),
                str(row["timezone"]),
                str(row["gender"]),
                str(row["calendar"]),
                str(row["timestamp"]),
            )
            group = grouped[key]
            group["analysis"][row["analysis_type"]] = parse_legacy_item(str(row["data"]))
            group["max_id"] = max(group["max_id"], int(row["id"]))

        inserted = 0
        skipped = 0

        for (date, timezone, gender, calendar, ts), payload in grouped.items():
            birth_info = {
                "date": date,
                "timezone": int(timezone),
                "gender": gender,
                "calendar": calendar,
            }

            legacy_key_plain = f"{date}|{timezone}|{gender}|{calendar}|legacy|legacy|legacy|{ts}|{payload['max_id']}"
            cache_key = hashlib.sha256(legacy_key_plain.encode("utf-8")).hexdigest()

            new_cursor = new_conn.cursor()
            new_cursor.execute(
                "SELECT id FROM analysis_results WHERE cache_key = ? LIMIT 1",
                (cache_key,),
            )
            if new_cursor.fetchone():
                skipped += 1
                continue

            analysis = payload["analysis"]
            total_execution_time = float(
                sum(float(item.get("execution_time", 0.0)) for item in analysis.values())
            )
            total_token_count = int(sum(int(item.get("token_count", 0)) for item in analysis.values()))

            new_cursor.execute(
                """
                INSERT INTO analysis_results (
                  cache_key,
                  birth_info_json,
                  text_description,
                  provider,
                  model,
                  prompt_version,
                  total_execution_time,
                  total_token_count,
                  created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cache_key,
                    json.dumps(birth_info, ensure_ascii=False),
                    "历史迁移数据：旧系统未持久化命盘文本描述。",
                    "legacy",
                    "legacy",
                    "legacy",
                    total_execution_time,
                    total_token_count,
                    ts,
                ),
            )
            if new_cursor.lastrowid is None:
                raise RuntimeError("failed to insert migrated result")
            result_id = int(new_cursor.lastrowid)

            for analysis_type, item in analysis.items():
                new_cursor.execute(
                    """
                    INSERT INTO analysis_items (
                      result_id,
                      analysis_type,
                      content,
                      execution_time,
                      input_tokens,
                      output_tokens,
                      token_count,
                      created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result_id,
                        analysis_type,
                        item["content"],
                        float(item["execution_time"]),
                        int(item["input_tokens"]),
                        int(item["output_tokens"]),
                        int(item["token_count"]),
                        ts,
                    ),
                )

            inserted += 1

        new_conn.commit()
        return inserted, skipped
    finally:
        legacy_conn.close()
        new_conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate legacy app.py results table into backend schema")
    parser.add_argument(
        "--legacy-db",
        default=str(Path(__file__).resolve().parents[2] / "data.db"),
        help="legacy sqlite db path (default: repo_root/data.db)",
    )
    parser.add_argument(
        "--new-db",
        default=str(Path(__file__).resolve().parents[1] / "data.db"),
        help="new backend sqlite db path (default: backend/data.db)",
    )
    args = parser.parse_args()

    inserted, skipped = migrate_legacy_results(Path(args.legacy_db), Path(args.new_db))
    print(f"legacy migration done. inserted={inserted}, skipped={skipped}")


if __name__ == "__main__":
    main()
