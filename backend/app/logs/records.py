from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..models import ProviderId, TokenTotals


@dataclass(frozen=True, slots=True)
class LogRecord:
    observed_at: datetime
    provider: ProviderId
    project: str
    model: str
    #: Sitzung, aus der die Nachricht stammt – je Anbieter eindeutig.
    session: str
    totals: TokenTotals


@dataclass(slots=True)
class ReadResult:
    records: list[LogRecord] = field(default_factory=list)
    scanned_files: int = 0
    skipped_lines: int = 0


def token_count(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    return 0


def project_name(value: object, fallback: str = "Unbekannt") -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback

    normalized = value.strip().replace("\\", "/").rstrip("/")
    name = normalized.rsplit("/", 1)[-1]
    return name or fallback
