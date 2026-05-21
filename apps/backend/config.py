from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (parent of apps/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class Settings:
    """Centralised configuration read from environment variables."""

    _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://opencode.ai/zen/go/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-v4-flash")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai_compatible")

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8266"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes")

    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:5066,http://localhost:3000").split(",")
        if o.strip()
    ]

    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg://localhost/coomate")

    _prompt_path: Path = _PROJECT_ROOT / "docs" / "system_prompt.txt"


settings = Settings()
