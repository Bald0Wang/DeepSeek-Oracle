import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DEBUG = _to_bool(os.getenv("DEBUG", "false"))

    CORS_ORIGINS = _split_csv(os.getenv("CORS_ORIGINS", "http://localhost:5173"))

    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data.db"))
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    ANALYSIS_QUEUE = os.getenv("ANALYSIS_QUEUE", "analysis")

    IZTHON_SRC_PATH = os.getenv("IZTHON_SRC_PATH", "")
    REQUEST_TIMEOUT_S = int(os.getenv("REQUEST_TIMEOUT_S", "1800"))
    MAX_TASK_RETRY = int(os.getenv("MAX_TASK_RETRY", "2"))
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
    ORACLE_EAST_ONLY_MVP = _to_bool(os.getenv("ORACLE_EAST_ONLY_MVP", "true"))

    AUTH_TOKEN_EXPIRE_HOURS = int(os.getenv("AUTH_TOKEN_EXPIRE_HOURS", "72"))
    INVITE_ONLY = _to_bool(os.getenv("INVITE_ONLY", "false"))
    INVITE_CODES = _split_csv(os.getenv("INVITE_CODES", ""))
    ADMIN_EMAILS = _split_csv(os.getenv("ADMIN_EMAILS", ""))
    EMAIL_VERIFY_REQUIRED = _to_bool(os.getenv("EMAIL_VERIFY_REQUIRED", "true"), True)
    EMAIL_CODE_EXPIRE_MINUTES = int(os.getenv("EMAIL_CODE_EXPIRE_MINUTES", "10"))

    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USE_SSL = _to_bool(os.getenv("SMTP_USE_SSL", "true"), True)
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "DeepSeek Oracle")
    SMTP_TIMEOUT_S = int(os.getenv("SMTP_TIMEOUT_S", "20"))

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
    LLM_MODEL = os.getenv("LLM_MODEL", "mock-v1")
    PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1")

    VOLCANO_API_KEY = os.getenv("ARK_API_KEY", "")
    VOLCANO_MODEL = os.getenv("ARK_API_MODEL", os.getenv("ARK_API_model", ""))

    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    ALIYUN_API_KEY = os.getenv("ALIYUN_API_KEY", "")
    ALIYUN_BASE_URL = os.getenv(
        "ALIYUN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")

    QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
    QWEN_BASE_URL = os.getenv(
        "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
