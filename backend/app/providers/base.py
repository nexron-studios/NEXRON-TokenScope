from __future__ import annotations

from datetime import timezone
from email.utils import parsedate_to_datetime
from typing import Any, Protocol

import httpx

from ..models import ProviderId, ProviderStatus, ProviderUsage, SourceKind, UsageWindow
from ..normalize import extract_window, now


class Provider(Protocol):
    id: ProviderId
    name: str

    async def fetch(self, client: httpx.AsyncClient) -> ProviderUsage:
        """Liefert immer ein ProviderUsage – Fehler werden zu Status, nicht zu Exceptions."""
        ...


def build_error(
    provider_id: ProviderId,
    name: str,
    status: ProviderStatus,
    message: str,
    *,
    plan: str | None = None,
    source: SourceKind = "none",
    retry_after_seconds: float | None = None,
) -> ProviderUsage:
    return ProviderUsage(
        id=provider_id,
        name=name,
        plan=plan,
        windows=[],
        source=source,
        status=status,
        message=message,
        fetched_at=now(),
        retry_after_seconds=retry_after_seconds,
    )


def status_from_http(status_code: int) -> tuple[ProviderStatus, str]:
    if status_code in (401, 403):
        return (
            "unauthorized",
            "Token abgelehnt. Melde dich in der CLI neu an, dann erneut versuchen.",
        )
    if status_code == 404:
        return (
            "unexpected_shape",
            "Endpunkt nicht gefunden – die undokumentierte Route hat sich geändert.",
        )
    if status_code == 429:
        return ("rate_limited", "Anbieter drosselt gerade")
    if 500 <= status_code < 600:
        return ("unreachable", f"Anbieter meldet Serverfehler {status_code}.")
    return ("error", f"Unerwarteter HTTP-Status {status_code}.")


def parse_retry_after(response: httpx.Response) -> float | None:
    """Liest den ``Retry-After``-Header (Sekunden oder HTTP-Datum)."""
    raw = response.headers.get("retry-after")
    if not raw:
        return None

    raw = raw.strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        pass

    try:
        target = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if target is None:
        return None
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    return max(0.0, (target - now()).total_seconds())


def unwrap_payload(payload: Any, candidates: tuple[str, ...]) -> dict[str, Any] | None:
    """Findet den Block mit den Limitfenstern in einer verschachtelten Antwort."""
    if not isinstance(payload, dict):
        return None
    for key in candidates:
        nested = payload.get(key)
        if isinstance(nested, dict):
            return nested
    return payload


def windows_from_mapping(
    block: dict[str, Any],
    *,
    primary_keys: tuple[str, ...] = (),
    skip_keys: frozenset[str] = frozenset(),
) -> list[UsageWindow]:
    """Baut Fenster aus allen Unterobjekten, die einen Prozentwert enthalten."""
    windows: list[UsageWindow] = []
    for key, value in block.items():
        if key in skip_keys:
            continue
        extracted = extract_window(key, value, primary=key in primary_keys)
        if extracted is not None:
            windows.append(UsageWindow(**extracted))

    if windows and not any(window.primary for window in windows):
        # Kürzestes Fenster ist das für den Alltag interessante.
        shortest = min(
            windows,
            key=lambda window: window.window_minutes or 10**9,
        )
        shortest.primary = True

    windows.sort(key=lambda window: (window.window_minutes or 10**9, window.key))
    return windows
