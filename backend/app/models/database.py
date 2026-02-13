import sqlite3
from contextlib import contextmanager
from pathlib import Path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS analysis_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL UNIQUE,
  user_id INTEGER,
  status TEXT NOT NULL,
  progress INTEGER NOT NULL DEFAULT 0,
  step TEXT,
  birth_date TEXT NOT NULL,
  timezone INTEGER NOT NULL,
  gender TEXT NOT NULL,
  calendar TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  cache_key TEXT NOT NULL,
  result_id INTEGER,
  error_code TEXT,
  error_message TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  started_at DATETIME,
  finished_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_tasks_status_created_at
ON analysis_tasks(status, created_at DESC);

CREATE TABLE IF NOT EXISTS analysis_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cache_key TEXT NOT NULL UNIQUE,
  user_id INTEGER,
  birth_info_json TEXT NOT NULL,
  text_description TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  total_execution_time REAL NOT NULL,
  total_token_count INTEGER NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analysis_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  result_id INTEGER NOT NULL,
  analysis_type TEXT NOT NULL,
  content TEXT NOT NULL,
  execution_time REAL NOT NULL,
  input_tokens INTEGER NOT NULL,
  output_tokens INTEGER NOT NULL,
  token_count INTEGER NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(result_id, analysis_type)
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',
  is_active INTEGER NOT NULL DEFAULT 1,
  invite_code_used TEXT,
  last_login_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_role_created_at
ON users(role, created_at DESC);

CREATE TABLE IF NOT EXISTS system_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id TEXT,
  method TEXT,
  path TEXT,
  status_code INTEGER,
  duration_ms INTEGER,
  level TEXT NOT NULL DEFAULT 'info',
  message TEXT,
  user_id INTEGER,
  user_email TEXT,
  ip TEXT,
  user_agent TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_system_logs_created_at
ON system_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_system_logs_path_created_at
ON system_logs(path, created_at DESC);

CREATE TABLE IF NOT EXISTS email_verification_codes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  purpose TEXT NOT NULL,
  code_hash TEXT NOT NULL,
  expires_at DATETIME NOT NULL,
  consumed_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_codes_lookup
ON email_verification_codes(email, purpose, created_at DESC);

CREATE TABLE IF NOT EXISTS life_kline_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  source_result_id INTEGER,
  birth_info_json TEXT NOT NULL,
  sparse_json TEXT NOT NULL,
  kline_json TEXT NOT NULL,
  summary_json TEXT NOT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_life_kline_user_updated
ON life_kline_profiles(user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS monthly_calendars (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  month_key TEXT NOT NULL,
  source_result_id INTEGER,
  birth_info_json TEXT NOT NULL,
  calendar_json TEXT NOT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, month_key)
);

CREATE INDEX IF NOT EXISTS idx_monthly_calendar_user_month
ON monthly_calendars(user_id, month_key);

CREATE TABLE IF NOT EXISTS oracle_conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  title TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_oracle_conversations_user_updated
ON oracle_conversations(user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS oracle_turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  user_query TEXT NOT NULL,
  context_summary TEXT NOT NULL,
  status TEXT NOT NULL,
  plan_steps_json TEXT NOT NULL,
  answer_text TEXT NOT NULL,
  action_items_json TEXT NOT NULL,
  follow_up_questions_json TEXT NOT NULL,
  safety_disclaimer_level TEXT NOT NULL,
  error_message TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_oracle_turns_conversation_created
ON oracle_turns(conversation_id, created_at ASC);

CREATE TABLE IF NOT EXISTS divination_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  divination_type TEXT NOT NULL,
  question_text TEXT NOT NULL,
  birth_info_json TEXT,
  occurred_at TEXT,
  result_json TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_divination_records_user_created
ON divination_records(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_divination_records_user_type_created
ON divination_records(user_id, divination_type, created_at DESC);

CREATE TABLE IF NOT EXISTS scheduler_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_name TEXT NOT NULL,
  run_key TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(job_name, run_key)
);
"""


def get_connection(database_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(database_path: str) -> None:
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    with get_connection(database_path) as conn:
        conn.executescript(SCHEMA_SQL)
        _migrate_user_scope_columns(conn)
        _migrate_insight_tables(conn)
        _migrate_oracle_chat_tables(conn)
        _migrate_divination_records_table(conn)
        conn.commit()


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return any(str(row["name"]) == column for row in cursor.fetchall())


def _migrate_user_scope_columns(conn: sqlite3.Connection) -> None:
    if not _has_column(conn, "analysis_tasks", "user_id"):
        conn.execute("ALTER TABLE analysis_tasks ADD COLUMN user_id INTEGER")
    if not _has_column(conn, "analysis_results", "user_id"):
        conn.execute("ALTER TABLE analysis_results ADD COLUMN user_id INTEGER")

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tasks_user_created_at
        ON analysis_tasks(user_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_results_user_created_at
        ON analysis_results(user_id, created_at DESC)
        """
    )

    # Backfill result ownership when task ownership is available.
    conn.execute(
        """
        UPDATE analysis_results
        SET user_id = (
          SELECT t.user_id
          FROM analysis_tasks t
          WHERE t.result_id = analysis_results.id
            AND t.user_id IS NOT NULL
          ORDER BY t.id DESC
          LIMIT 1
        )
        WHERE user_id IS NULL
        """
    )


def _migrate_insight_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS life_kline_profiles (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          source_result_id INTEGER,
          birth_info_json TEXT NOT NULL,
          sparse_json TEXT NOT NULL,
          kline_json TEXT NOT NULL,
          summary_json TEXT NOT NULL,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(user_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS monthly_calendars (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          month_key TEXT NOT NULL,
          source_result_id INTEGER,
          birth_info_json TEXT NOT NULL,
          calendar_json TEXT NOT NULL,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(user_id, month_key)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scheduler_runs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          job_name TEXT NOT NULL,
          run_key TEXT NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(job_name, run_key)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_life_kline_user_updated
        ON life_kline_profiles(user_id, updated_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_monthly_calendar_user_month
        ON monthly_calendars(user_id, month_key)
        """
    )


def _migrate_oracle_chat_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS oracle_conversations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          title TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_oracle_conversations_user_updated
        ON oracle_conversations(user_id, updated_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS oracle_turns (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          conversation_id INTEGER NOT NULL,
          user_query TEXT NOT NULL,
          context_summary TEXT NOT NULL,
          status TEXT NOT NULL,
          plan_steps_json TEXT NOT NULL,
          answer_text TEXT NOT NULL,
          action_items_json TEXT NOT NULL,
          follow_up_questions_json TEXT NOT NULL,
          safety_disclaimer_level TEXT NOT NULL,
          error_message TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_oracle_turns_conversation_created
        ON oracle_turns(conversation_id, created_at ASC)
        """
    )


def _migrate_divination_records_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS divination_records (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          divination_type TEXT NOT NULL,
          question_text TEXT NOT NULL,
          birth_info_json TEXT,
          occurred_at TEXT,
          result_json TEXT NOT NULL,
          provider TEXT NOT NULL,
          model TEXT NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_divination_records_user_created
        ON divination_records(user_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_divination_records_user_type_created
        ON divination_records(user_id, divination_type, created_at DESC)
        """
    )


@contextmanager
def db_cursor(database_path: str):
    conn = get_connection(database_path)
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
