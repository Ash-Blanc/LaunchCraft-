"""Application settings, read from environment variables only.

Secrets (PayPal client secret, AI provider key) live here and nowhere else.
They are never returned by any API route and never logged.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

PAYPAL_SANDBOX_BASE = "https://api-m.sandbox.paypal.com"


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./launchcraft.db"
    paypal_client_id: str = ""
    paypal_client_secret: str = field(default="", repr=False)
    # Only "sandbox" is accepted. Production is deliberately unsupported for the hackathon.
    paypal_env: str = "sandbox"
    ai_api_key: str = field(default="", repr=False)
    ai_model: str = ""
    frontend_origin: str = "http://localhost:3000"
    http_timeout_seconds: float = 15.0

    @property
    def paypal_base_url(self) -> str:
        if self.paypal_env != "sandbox":
            raise RuntimeError("Only PAYPAL_ENV=sandbox is supported in this build.")
        return PAYPAL_SANDBOX_BASE

    @property
    def paypal_configured(self) -> bool:
        return bool(self.paypal_client_id and self.paypal_client_secret)

    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./launchcraft.db"),
        paypal_client_id=os.getenv("PAYPAL_CLIENT_ID", ""),
        paypal_client_secret=os.getenv("PAYPAL_CLIENT_SECRET", ""),
        paypal_env=os.getenv("PAYPAL_ENV", "sandbox"),
        ai_api_key=os.getenv("AI_API_KEY", ""),
        ai_model=os.getenv("AI_MODEL", ""),
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:3000"),
        http_timeout_seconds=float(os.getenv("HTTP_TIMEOUT_SECONDS", "15")),
    )
