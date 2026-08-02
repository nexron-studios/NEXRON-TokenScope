from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ProviderId = Literal["claude", "codex"]

ProviderStatus = Literal[
    "ok",
    "disabled",
    "auth_missing",
    "auth_expired",
    "unauthorized",
    "rate_limited",
    "unreachable",
    "unexpected_shape",
    "error",
]

SourceKind = Literal["api", "logs", "cli", "demo", "none"]


class UsageWindow(BaseModel):
    """Ein Limitfenster eines Anbieters, normalisiert auf Prozent."""

    key: str
    label: str
    used_percent: float = Field(ge=0, le=100)
    remaining_percent: float = Field(ge=0, le=100)
    resets_at: datetime | None = None
    window_minutes: int | None = None
    primary: bool = False


class ProviderUsage(BaseModel):
    id: ProviderId
    name: str
    plan: str | None = None
    windows: list[UsageWindow] = Field(default_factory=list)
    source: SourceKind = "none"
    status: ProviderStatus = "error"
    message: str | None = None
    #: Zeitpunkt, zu dem *diese Werte* geholt wurden – bei zwischengespeicherten
    #: Daten also älter als der letzte Poll.
    fetched_at: datetime
    #: Werte stammen aus dem letzten geglückten Abruf, nicht aus diesem.
    stale: bool = False
    #: Warum der frische Abruf scheiterte, während die Werte weiter gelten.
    warning: str | None = None
    #: Vom Anbieter gefordete Wartezeit (`Retry-After`) bei Ratenbegrenzung.
    retry_after_seconds: float | None = None

    @property
    def is_usable(self) -> bool:
        return self.status == "ok" and bool(self.windows)


class UsageResponse(BaseModel):
    generated_at: datetime
    poll_interval_seconds: int
    demo_mode: bool
    providers: list[ProviderUsage]


class HistoryPoint(BaseModel):
    captured_at: datetime
    used_percent: float


class HistorySeries(BaseModel):
    provider: ProviderId
    window_key: str
    label: str
    points: list[HistoryPoint]


class HistoryResponse(BaseModel):
    since: datetime
    series: list[HistorySeries]


class TokenTotals(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_write_tokens
            + self.cache_read_tokens
        )


class LogBucket(BaseModel):
    """Aggregat einer Gruppierung (Tag, Projekt oder Modell)."""

    key: str
    label: str
    provider: ProviderId
    messages: int
    totals: TokenTotals


class LogSummary(BaseModel):
    since: datetime
    days: int
    group_by: Literal["day", "project", "model", "provider"]
    scanned_files: int
    skipped_lines: int
    totals: TokenTotals
    buckets: list[LogBucket]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    demo_mode: bool
    loopback_only: bool
    history_enabled: bool
    last_poll_at: datetime | None
    last_poll_error: str | None
    sources: dict[str, bool]
