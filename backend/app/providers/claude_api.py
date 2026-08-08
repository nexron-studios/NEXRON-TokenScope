from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import Settings
from ..credentials import CredentialError, load_claude_credential
from ..models import ProviderUsage
from ..normalize import now, redact
from .base import (
    build_error,
    parse_retry_after,
    status_from_http,
    unwrap_payload,
    windows_from_mapping,
)

logger = logging.getLogger(__name__)

# Nicht-Fenster-Felder, die in der Antwort neben den Limits stehen können.
_SKIP_KEYS = frozenset(
    {
        "plan",
        "plan_type",
        "subscription_type",
        "organization",
        "account",
        "user",
        "credits",
    }
)

# Fenster, die wir anzeigen. Der Endpunkt liefert daneben interne
# Codename-Buckets (z. B. "nimbus_quill") ohne Fenstergröße und Reset.
_DISPLAY_KEYS = frozenset(
    {
        "five_hour",
        "seven_day",
        "seven_day_opus",
        "seven_day_oauth_apps",
    }
)

_PLAN_LABELS = {
    "max": "Max",
    "pro": "Pro",
    "team": "Team",
    "enterprise": "Enterprise",
    "free": "Free",
}


class ClaudeProvider:
    """Fragt den undokumentierten OAuth-Usage-Endpunkt von Claude Code ab."""

    id = "claude"
    name = "Claude Code"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def fetch(self, client: httpx.AsyncClient) -> ProviderUsage:
        settings = self._settings

        try:
            credential = load_claude_credential(
                settings.claude_credentials_path,
                settings.claude_keychain_service,
            )
        except CredentialError as exc:
            return build_error(self.id, self.name, exc.kind, str(exc))

        plan = _PLAN_LABELS.get((credential.plan or "").lower(), credential.plan)

        if credential.is_expired:
            return build_error(
                self.id,
                self.name,
                "auth_expired",
                "Token abgelaufen. Die CLI erneuert ihn beim nächsten Start.",
                plan=plan,
            )

        try:
            response = await client.get(
                settings.claude_usage_url,
                headers={
                    "Authorization": f"Bearer {credential.access_token}",
                    "anthropic-beta": settings.claude_oauth_beta,
                    "Accept": "application/json",
                },
            )
        except httpx.TimeoutException:
            return build_error(
                self.id, self.name, "unreachable", "Zeitüberschreitung.", plan=plan
            )
        except httpx.HTTPError as exc:
            message = redact(str(exc) or exc.__class__.__name__, credential.access_token)
            return build_error(self.id, self.name, "unreachable", message, plan=plan)

        if response.status_code != 200:
            status, message = status_from_http(response.status_code)
            return build_error(
                self.id,
                self.name,
                status,
                message,
                plan=plan,
                retry_after_seconds=parse_retry_after(response),
            )

        try:
            payload: Any = response.json()
        except ValueError:
            return build_error(
                self.id,
                self.name,
                "unexpected_shape",
                "Antwort war kein JSON.",
                plan=plan,
            )

        block = unwrap_payload(payload, ("rate_limits", "usage", "limits", "data"))
        if block is None:
            return build_error(
                self.id,
                self.name,
                "unexpected_shape",
                "Unbekanntes Antwortformat.",
                plan=plan,
            )

        windows = windows_from_mapping(
            block,
            primary_keys=("five_hour", "primary"),
            skip_keys=_SKIP_KEYS,
        )

        if not windows:
            logger.warning(
                "Claude-Usage-Antwort ohne erkennbare Limitfenster (Schlüssel: %s)",
                sorted(block)[:12],
            )
            return build_error(
                self.id,
                self.name,
                "unexpected_shape",
                "Keine Limitfenster in der Antwort – Format hat sich geändert.",
                plan=plan,
            )

        named = [window for window in windows if window.key in _DISPLAY_KEYS]
        if named:
            dropped = [window.key for window in windows if window.key not in _DISPLAY_KEYS]
            if dropped:
                logger.debug("Unbenannte Limitfenster ausgeblendet: %s", dropped)
            if not any(window.primary for window in named):
                # windows_from_mapping sortiert nach Fenstergröße.
                named[0].primary = True
            windows = named

        raw_plan = block.get("plan") or block.get("subscription_type")
        if isinstance(raw_plan, str) and raw_plan:
            plan = _PLAN_LABELS.get(raw_plan.lower(), raw_plan)

        return ProviderUsage(
            id=self.id,
            name=self.name,
            plan=plan,
            windows=windows,
            source="api",
            status="ok",
            fetched_at=now(),
        )
