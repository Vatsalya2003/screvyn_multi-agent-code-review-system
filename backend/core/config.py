"""
Centralized configuration — loads ALL secrets from environment variables.

LOCAL DEV:   secrets live in backend/.env (never committed)
PRODUCTION:  secrets live in Railway/Vercel dashboard env vars
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)


def _require(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        print(f"\n  ERROR: Required env var '{key}' is not set.")
        print(f"  Set it in backend/.env (local) or hosting dashboard.\n")
        sys.exit(1)
    return value


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = field(default_factory=lambda: _require("GEMINI_API_KEY"))
    gemini_model: str = field(default_factory=lambda: _optional("GEMINI_MODEL", "gemini-2.0-flash"))
    github_app_id: str = field(default_factory=lambda: _optional("GITHUB_APP_ID"))
    github_private_key_path: str = field(default_factory=lambda: _optional("GITHUB_PRIVATE_KEY_PATH"))
    github_webhook_secret: str = field(default_factory=lambda: _optional("GITHUB_WEBHOOK_SECRET"))
    redis_url: str = field(default_factory=lambda: _optional("REDIS_URL"))
    firebase_project_id: str = field(default_factory=lambda: _optional("FIREBASE_PROJECT_ID"))
    firebase_credentials_path: str = field(default_factory=lambda: _optional("FIREBASE_CREDENTIALS_PATH"))
    slack_webhook_url: str = field(default_factory=lambda: _optional("SLACK_WEBHOOK_URL"))
    teams_webhook_url: str = field(default_factory=lambda: _optional("TEAMS_WEBHOOK_URL"))
    resend_api_key: str = field(default_factory=lambda: _optional("RESEND_API_KEY"))
    notification_email_from: str = field(
        default_factory=lambda: _optional("NOTIFICATION_EMAIL_FROM", "reviews@screvyn.dev")
    )
    environment: str = field(default_factory=lambda: _optional("ENVIRONMENT", "development"))
    log_level: str = field(default_factory=lambda: _optional("LOG_LEVEL", "INFO"))
    rate_limit_monthly: int = 50

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
