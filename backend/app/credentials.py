from __future__ import annotations

import base64
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .normalize import parse_timestamp, now


class CredentialError(RuntimeError):
    """Token konnte nicht gelesen werden."""

    def __init__(self, message: str, *, kind: str = "auth_missing") -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class Credential:
    """Ein OAuth-Token samt Metadaten.

    ``__repr__`` und ``__str__`` sind bewusst redigiert: Ein versehentliches
    ``print(cred)`` oder ein Traceback darf niemals Tokenmaterial ausgeben.
    """

    access_token: str
    account_id: str | None = None
    plan: str | None = None
    expires_at: datetime | None = None
    extras: dict[str, Any] = field(default_factory=dict, repr=False)

    def __repr__(self) -> str:  # pragma: no cover - triviale Maskierung
        return (
            f"Credential(access_token='***', account_id={self.account_id!r}, "
            f"plan={self.plan!r}, expires_at={self.expires_at!r})"
        )

    __str__ = __repr__

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= now()


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CredentialError(f"Datei nicht gefunden: {path}") from exc
    except PermissionError as exc:
        raise CredentialError(f"Keine Leserechte für {path}") from exc
    except OSError as exc:
        raise CredentialError(f"{path} nicht lesbar ({exc.strerror}).") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        # Die CLI schreibt die Datei beim Token-Refresh neu; ein halb
        # geschriebener Stand ist ein normaler Zustand, kein Fehlerfall.
        raise CredentialError(
            f"{path.name} ist gerade nicht gültig (evtl. Token-Refresh).",
            kind="auth_missing",
        ) from exc

    if not isinstance(payload, dict):
        raise CredentialError(f"{path.name} enthält kein JSON-Objekt.")
    return payload


def _read_macos_keychain(service: str) -> dict[str, Any] | None:
    """Liest den Keychain-Eintrag der Claude-CLI auf macOS."""
    if sys.platform != "darwin":
        return None
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        payload = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _jwt_expires_at(token: str) -> datetime | None:
    """Liest nur den unkritischen ``exp``-Claim aus einem JWT.

    Die Signatur wird hier bewusst nicht als Echtheitsnachweis verwendet; der
    Server prüft sie beim eigentlichen Request. Für den lokalen Hinweis reicht
    der Zeitstempel aus dem bereits vorhandenen Token.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        encoded = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None
    return parse_timestamp(payload.get("exp"))


def load_claude_credential(
    credentials_path: Path,
    keychain_service: str,
) -> Credential:
    """Liest den Claude-Code-Token frisch ein.

    Reihenfolge: macOS-Keychain, danach ``~/.claude/.credentials.json``.
    Die CLI erneuert den Token laufend – deshalb kein Caching.
    """
    payload = _read_macos_keychain(keychain_service)
    if payload is None:
        payload = _read_json_file(credentials_path)

    oauth = payload.get("claudeAiOauth")
    if not isinstance(oauth, dict):
        oauth = payload

    token = oauth.get("accessToken") or oauth.get("access_token")
    if not isinstance(token, str) or not token:
        raise CredentialError("Kein accessToken in den Claude-Credentials.")

    expires_at = parse_timestamp(oauth.get("expiresAt") or oauth.get("expires_at"))
    plan = oauth.get("subscriptionType") or oauth.get("subscription_type")

    return Credential(
        access_token=token,
        plan=str(plan) if plan else None,
        expires_at=expires_at,
        extras={"rate_limit_tier": oauth.get("rateLimitTier")},
    )


def load_codex_credential(auth_path: Path) -> Credential:
    """Liest den Codex-Token aus ``~/.codex/auth.json``."""
    payload = _read_json_file(auth_path)

    tokens = payload.get("tokens")
    if not isinstance(tokens, dict):
        raise CredentialError("Kein tokens-Objekt in der Codex-auth.json.")

    token = tokens.get("access_token")
    if not isinstance(token, str) or not token:
        raise CredentialError("Kein access_token in der Codex-auth.json.")

    account_id = tokens.get("account_id")

    return Credential(
        access_token=token,
        account_id=str(account_id) if account_id else None,
        expires_at=_jwt_expires_at(token),
        extras={"auth_mode": payload.get("auth_mode")},
    )
