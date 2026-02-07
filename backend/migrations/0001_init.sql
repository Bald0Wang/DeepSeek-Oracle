CREATE TABLE IF NOT EXISTS analysis_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL UNIQUE,
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
