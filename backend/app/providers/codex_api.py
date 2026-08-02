from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from ..config import Settings
from ..credentials import CredentialError, load_codex_credential
from ..logs.codex_jsonl import latest_codex_rate_limits
from ..models import ProviderUsage, SourceKind, UsageWindow
from ..normalize import extract_window, now, parse_timestamp, redact
from .base import build_error, parse_retry_after, status_from_http, unwrap_payload

logger = logging.getLogger(__name__)

_SKIP_KEYS = frozenset(
    {
        "limit_id",
        "limit_name",
        "credits",
        "plan_type",
        "individual_limit",
        "spend_control_reached",
        "rate_limit_reached_type",
        "_observed_at",
    }
)

_PLAN_LABELS = {
    "plus": "Plus",
    "pro": "Pro",
    "team": "Team",
    "business": "Business",
    "enterprise": "Enterprise",
    "free": "Free",
}


def _windows_from_rate_limits(block: dict[str, Any]) -> list[UsageWindow]:
    """``{primary: {...}, secondary: {...}}`` → normalisierte Fenster."""
    windows: list[UsageWindow] = []
    reference = parse_timestamp(block.get("_observed_at"))

    for key, value in block.items():
        if key in _SKIP_KEYS or not isinstance(value, dict):
            continue
        extracted = extract_window(
            key,
            value,
            reference=reference,
            primary=key == "primary",
        )
        if extracted is None:
            continue
        windows.append(UsageWindow(**extracted))

    windows.sort(key=lambda window: (window.window_minutes or 10**9, window.key))
    return windows


class CodexProvider:
    """Fragt das Codex-Kontingent ab: HTTP zuerst, danach lokale Rollout-Logs."""

    id = "codex"
    name = "Codex"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def fetch(self, client: httpx.AsyncClient) -> ProviderUsage:
        api_result = await self._fetch_api(client)
        if api_result.status == "ok":
            return api_result

        for fallback in (self._fetch_from_logs, self._fetch_from_cli):
            result = await fallback()
            if result is not None and result.status == "ok":
                result.message = f"Fallback aktiv: {api_result.message or 'API nicht verfügbar'}"
                return result

        return api_result

    # --- Primärquelle -----------------------------------------------------

    async def _fetch_api(self, client: httpx.AsyncClient) -> ProviderUsage:
        settings = self._settings

        try:
            credential = load_codex_credential(settings.codex_auth_path)
        except CredentialError as exc:
            return build_error(self.id, self.name, exc.kind, str(exc))

        headers = {
            "Authorization": f"Bearer {credential.access_token}",
            "Accept": "application/json",
        }
        if credential.account_id:
            headers["chatgpt-account-id"] = credential.account_id

        try:
            response = await client.get(settings.codex_usage_url, headers=headers)
        except httpx.TimeoutException:
            return build_error(self.id, self.name, "unreachable", "Zeitüberschreitung.")
        except httpx.HTTPError as exc:
            message = redact(str(exc) or exc.__class__.__name__, credential.access_token)
            return build_error(self.id, self.name, "unreachable", message)

        if response.status_code != 200:
            status, message = status_from_http(response.status_code)
            return build_error(
                self.id,
                self.name,
                status,
                message,
                retry_after_seconds=parse_retry_after(response),
            )

        try:
            payload: Any = response.json()
        except ValueError:
            return build_error(
                self.id, self.name, "unexpected_shape", "Antwort war kein JSON."
            )

        return self._from_payload(payload, source="api") or build_error(
            self.id,
            self.name,
            "unexpected_shape",
            "Keine Limitfenster in der Antwort – Format hat sich geändert.",
        )

    # --- Fallbacks --------------------------------------------------------

    async def _fetch_from_logs(self) -> ProviderUsage | None:
        if not self._settings.codex_log_fallback:
            return None

        block = await asyncio.to_thread(
            latest_codex_rate_limits, self._settings.codex_sessions_dir
        )
        if not block:
            return None
        return self._from_payload({"rate_limits": block}, source="logs")

    async def _fetch_from_cli(self) -> ProviderUsage | None:
        settings = self._settings
        if not settings.codex_cli_fallback:
            return None

        try:
            process = await asyncio.create_subprocess_exec(
                *settings.codex_cli_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(
                process.communicate(), timeout=settings.codex_cli_timeout_seconds
            )
        except (OSError, asyncio.TimeoutError, ValueError) as exc:
            logger.warning("codex-check-Fallback fehlgeschlagen: %s", exc)
            return None

        if process.returncode != 0 or not stdout:
            return None

        try:
            payload = json.loads(stdout.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            return None

        return self._from_payload(payload, source="cli")

    # --- Gemeinsame Normalisierung ---------------------------------------

    def _from_payload(self, payload: Any, *, source: SourceKind) -> ProviderUsage | None:
        block = unwrap_payload(payload, ("rate_limits", "usage", "limits", "data"))
        if block is None:
            return None

        windows = _windows_from_rate_limits(block)
        if not windows:
            logger.warning(
                "Codex-Antwort ohne erkennbare Limitfenster (Schlüssel: %s)",
                sorted(block)[:12],
            )
            return None

        raw_plan = block.get("plan_type")
        plan = (
            _PLAN_LABELS.get(str(raw_plan).lower(), str(raw_plan))
            if isinstance(raw_plan, str) and raw_plan
            else None
        )

        return ProviderUsage(
            id=self.id,
            name=self.name,
            plan=plan,
            windows=windows,
            source=source,
            status="ok",
            fetched_at=now(),
        )
