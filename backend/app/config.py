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
    # Wie frisch ein lokaler Codex-Logeintrag sein muss, um als aktueller Wert
    # zu gelten. Ältere echte Werte bleiben separat als Altstand sichtbar.
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

    # --- Token-Erneuerung über die CLI ------------------------------------
    # Ein abgelaufener Token wird nie selbst erneuert: weder der refresh_token
    # gelesen noch die Credentials geschrieben. Das darf nur, wer den Token
    # ausgestellt hat – die CLI. Läuft er ab, wird sie deshalb mit einem kurzen,
    # nicht interaktiven Kommando angestoßen, das nichts vom Kontingent
    # verbraucht. Eine leere Liste schaltet das für den Anbieter ab.
    #
    # Es muss ein Kommando sein, das den Token wirklich anfasst. `claude auth
    # status` tut das nicht: Es liest die Datei, meldet auch bei abgelaufenem
    # Token `loggedIn: true` und lässt sie unverändert – der Anstoß lief also
    # ins Leere und meldete dabei Erfolg. `claude doctor` erneuert
    # (gemessen an einer Kopie mit zurückgesetztem `expiresAt`: Datei neu
    # geschrieben, neues Ablaufdatum, rund drei Sekunden).
    claude_cli_refresh_command: list[str] = ["claude", "doctor"]
    # Bewusst leer, und das bleibt vorerst so: `codex login status` und
    # `codex doctor` lassen die `auth.json` nachweislich unberührt, und ein
    # `codex` im PATH gibt es hier gar nicht – die Binärdatei steckt in der
    # VS-Code-Erweiterung, unter einem Pfad, der jedes Update wechselt. Die
    # Mechanik ist anbieterunabhängig: Findet sich ein Kommando, das erneuert,
    # genügt es, es hier einzutragen.
    codex_cli_refresh_command: list[str] = []
    cli_refresh_timeout_seconds: float = 30.0
    cli_refresh_min_interval_seconds: float = 300.0

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
