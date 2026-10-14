from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

from ..claude_accounts import (
    CREDENTIALS_FILE,
    ClaudeAccount,
    is_default_dir,
    keychain_service_for,
)
from ..config import Settings
from ..credentials import Credential, CredentialError, load_claude_credential
from ..models import ProviderUsage, scope_key
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
    """Fragt den undokumentierten OAuth-Usage-Endpunkt für einen Login ab."""

    id = "claude"
    name = "Claude Code"

    def __init__(
        self, settings: Settings, account: ClaudeAccount, home: Path | None = None
    ) -> None:
        self._settings = settings
        self._account = account
        self._home = home or Path.home()
        self.account = account.info
        self.key = scope_key(self.id, account.info.id)
        #: Ordner, aus dem der zuletzt benutzte Token stammt.
        self._active_dir = account.config_dirs[0]

    @property
    def refresh_env(self) -> dict[str, str]:
        if is_default_dir(self._active_dir, self._home):
            return {}
        return {"CLAUDE_CONFIG_DIR": str(self._active_dir)}

    def _load_credential(self) -> Credential:
        """Der erste noch gültige Token unter den Ordnern dieses Accounts.

        Hängen zwei Ordner am selben Account, darf ein abgelaufener Token im
        einen nicht verdecken, dass der andere gerade frisch ist.
        """
        expired: tuple[Credential, Path] | None = None
        failure: CredentialError | None = None
        for directory in self._account.config_dirs:
            try:
                credential = load_claude_credential(
                    directory / CREDENTIALS_FILE,
                    keychain_service_for(
                        directory, self._home, self._settings.claude_keychain_service
                    ),
                )
            except CredentialError as exc:
                failure = failure or exc
                continue
            if not credential.is_expired:
                self._active_dir = directory
                return credential
            expired = expired or (credential, directory)

        if expired is not None:
            self._active_dir = expired[1]
            return expired[0]
        raise failure or CredentialError("Keine Claude-Anmeldung gefunden.")

    async def fetch(self, client: httpx.AsyncClient) -> ProviderUsage:
        settings = self._settings

        try:
            credential = self._load_credential()
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
            status, message = status_from_http(
                response.status_code,
                content_type=response.headers.get("content-type"),
            )
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
