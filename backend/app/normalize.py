from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Feldnamen, unter denen die undokumentierten Endpunkte den Verbrauch melden.
_USED_KEYS = (
    "utilization",
    "used_percent",
    "usedPercent",
    "percent_used",
    "percentUsed",
    "usage_percent",
)
_REMAINING_KEYS = (
    "remaining_percent",
    "remainingPercent",
    "percent_remaining",
)
_RESET_KEYS = (
    "resets_at",
    "resetsAt",
    "reset_at",
    "resetAt",
    "resets_at_utc",
    "next_reset",
    "nextReset",
)
_RESET_DELTA_KEYS = (
    "resets_in_seconds",
    "resetsInSeconds",
    "seconds_until_reset",
)
_WINDOW_MINUTE_KEYS = ("window_minutes", "windowMinutes", "window_size_minutes")

# Der Claude-Endpunkt nennt die Fenstergröße nicht, nur den Schlüssel.
KNOWN_WINDOW_MINUTES = {
    "five_hour": 300,
    "seven_day": 10080,
    "seven_day_opus": 10080,
    "seven_day_oauth_apps": 10080,
    "monthly": 43200,
}


def now() -> datetime:
    return datetime.now(timezone.utc)


def clamp_percent(value: float) -> float:
    return max(0.0, min(100.0, round(float(value), 2)))


def to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().rstrip("%"))
        except ValueError:
            return None
    return None


def to_int(value: Any) -> int | None:
    number = to_float(value)
    return int(number) if number is not None else None


def parse_timestamp(value: Any) -> datetime | None:
    """Akzeptiert ISO-8601-Strings sowie Unix-Sekunden und -Millisekunden."""
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        seconds = float(value)
        if seconds > 1e11:  # Millisekunden
            seconds /= 1000.0
        if seconds <= 0:
            return None
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            return parse_timestamp(int(text))
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    return None


def first_present(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def window_label(key: str, window_minutes: int | None) -> str:
    """Menschenlesbares Label; bevorzugt die bekannte Fenstergröße."""
    known = {
        "five_hour": "5 Stunden",
        "seven_day": "7 Tage",
        "seven_day_opus": "7 Tage · Opus",
        "seven_day_oauth_apps": "7 Tage · Apps",
        "monthly": "30 Tage",
    }
    if key in known:
        return known[key]

    if window_minutes:
        if window_minutes % 1440 == 0:
            days = window_minutes // 1440
            return f"{days} Tag" if days == 1 else f"{days} Tage"
        if window_minutes % 60 == 0:
            hours = window_minutes // 60
            return f"{hours} Stunde" if hours == 1 else f"{hours} Stunden"
        return f"{window_minutes} Minuten"

    return key.replace("_", " ").strip().capitalize()


def extract_window(
    key: str,
    payload: Any,
    *,
    reference: datetime | None = None,
    primary: bool = False,
) -> dict[str, Any] | None:
    """Formt einen unbekannt strukturierten Fenster-Block in unser Schema.

    Gibt ``None`` zurück, wenn der Block keinen Prozentwert enthält – so
    überlebt die Normalisierung eine Schemaänderung beim Anbieter, statt die
    ganze Antwort zu verwerfen.
    """
    if not isinstance(payload, dict):
        return None

    used = to_float(first_present(payload, _USED_KEYS))
    if used is None:
        remaining = to_float(first_present(payload, _REMAINING_KEYS))
        if remaining is None:
            return None
        used = 100.0 - remaining

    used = clamp_percent(used)
    window_minutes = to_int(
        first_present(payload, _WINDOW_MINUTE_KEYS)
    ) or KNOWN_WINDOW_MINUTES.get(key)

    resets_at = parse_timestamp(first_present(payload, _RESET_KEYS))
    if resets_at is None:
        delta = to_float(first_present(payload, _RESET_DELTA_KEYS))
        if delta is not None and delta >= 0:
            base = reference or now()
            resets_at = datetime.fromtimestamp(base.timestamp() + delta, tz=timezone.utc)

    return {
        "key": key,
        "label": window_label(key, window_minutes),
        "used_percent": used,
        "remaining_percent": clamp_percent(100.0 - used),
        "resets_at": resets_at,
        "window_minutes": window_minutes,
        "primary": primary,
    }


def redact(text: str, *secrets: str | None) -> str:
    """Entfernt Tokenmaterial aus Fehlermeldungen, bevor es geloggt wird."""
    cleaned = text
    for secret in secrets:
        if secret and len(secret) >= 8:
            cleaned = cleaned.replace(secret, "***")
    return cleaned
