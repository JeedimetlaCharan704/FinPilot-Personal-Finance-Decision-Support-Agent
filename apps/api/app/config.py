# FinPilot API — backend configuration via environment variables.
#
# SECURITY:
# - Service-role and LLM keys are server-only. Never expose them to the
#   browser, never log them, never commit them.
# - Missing optional keys degrade gracefully (DbHealth reports
#   "not_configured") instead of crashing the whole app.
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    # apps/api/app/config.py -> parents: app -> api -> apps -> repo root
    return Path(__file__).resolve().parents[3]


_REPO_ROOT = _repo_root()
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- app identity ---
    app_name: str = "FinPilot API"
    service_name: str = "finpilot-api"
    version: str = "0.3.0"

    # --- CORS ---
    cors_origins: str = "http://localhost:3000"

    # --- LLM (Phase 3: config only; not wired yet) ---
    llm_provider: str = "xai"  # xai | ollama
    xai_api_key: str | None = None
    xai_model: str = "grok-4.5"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"

    # --- Supabase (Phase 3: config + health; storage-only) ---
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None

    # --- data ---
    demo_data_path: str = "data/demo_data.csv"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()