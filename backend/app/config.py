from __future__ import annotations

import ipaddress
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    """Konfiguration des lokalen Dienstes.

    Alle Werte lassen sich über Umgebungsvariablen mit dem Präfix
    ``NEXRON_TOKENSCOPE_`` oder über ``backend/.env`` überschreiben.
    """

    model_config = SettingsConfigDict(
        env_prefix="NEXRON_TOKENSCOPE_",
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Server -----------------------------------------------------------
    host: str = "127.0.0.1"
    port: int = 8787
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]

    # --- Polling ----------------------------------------------------------
    poll_interval_seconds: int = 60
    request_timeout_seconds: float = 10.0
    manual_refresh_min_interval_seconds: float = 5.0
    demo_mode: bool = False
    # Wie lange ein Anbieter höchstens mit dem letzten guten Wert überbrückt
    # wird. Danach ist die Zahl zu alt, um noch etwas auszusagen – die Kachel
    # zeigt dann lieber nichts als etwas Falsches.
    max_bridge_minutes: float = 30.0

    # --- Claude Code ------------------------------------------------------
    claude_enabled: bool = True
    claude_credentials_path: Path = Path.home() / ".claude" / ".credentials.json"
    claude_keychain_service: str = "Claude Code-credentials"
    claude_usage_url: str = "https://api.anthropic.com/api/oauth/usage"
    claude_oauth_beta: str = "oauth-2025-04-20"
    claude_projects_dir: Path = Path.home() / ".claude" / "projects"

    # --- Codex ------------------------------------------------------------
    codex_enabled: bool = True
    codex_auth_path: Path = Path.home() / ".codex" / "auth.json"
    codex_usage_url: str = "https://chatgpt.com/backend-api/codex/usage"
    codex_sessions_dir: Path = Path.home() / ".codex" / "sessions"
    # Fällt auf die zuletzt in den Rollout-Logs gemeldeten rate_limits zurück,
    # wenn der undokumentierte Endpunkt nicht antwortet.
    codex_log_fallback: bool = True
    # Optionaler zweiter Notnagel: `npx codex-check --json`.
    codex_cli_fallback: bool = False
    codex_cli_command: list[str] = ["npx", "--yes", "codex-check", "--json"]
    codex_cli_timeout_seconds: float = 45.0

    # --- Persistenz -------------------------------------------------------
    database_path: Path = BACKEND_ROOT / "data" / "usage.sqlite"
    history_enabled: bool = True
    history_retention_days: int = 90

    # --- Statisches Frontend ---------------------------------------------
    frontend_dist: Path = REPO_ROOT / "frontend" / "dist"

    @property
    def binds_loopback_only(self) -> bool:
        try:
            return ipaddress.ip_address(self.host).is_loopback
        except ValueError:
            return self.host in {"localhost", ""}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
