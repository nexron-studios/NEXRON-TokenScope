from __future__ import annotations

from datetime import timedelta
from typing import Annotated, Literal

import anyio.to_thread
from fastapi import APIRouter, Query, Request

from . import __version__
from .config import Settings
from .logs import LogStore
from .models import (
    HealthResponse,
    HistoryResponse,
    LogSummary,
    UsageResponse,
)
from .normalize import now
from .poller import UsagePoller
from .storage import SnapshotStore

router = APIRouter(prefix="/api")


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _poller(request: Request) -> UsagePoller:
    return request.app.state.poller


@router.get("/usage", response_model=UsageResponse, summary="Aktuelle Kontingente")
async def read_usage(
    request: Request,
    refresh: Annotated[bool, Query(description="Sofort neu abfragen")] = False,
) -> UsageResponse:
    poller = _poller(request)
    if refresh:
        # Der Nutzer hat ausdruecklich einen neuen Stand angefordert. Diese
        # Abfrage darf deshalb nicht an der Entprellung fuer normale Abrufe
        # haengen bleiben (anbieter-seitige Cooldowns gelten weiterhin).
        return await poller.refresh(force=True)
    return poller.snapshot


@router.get("/history", response_model=HistoryResponse, summary="Verlauf aus SQLite")
async def read_history(
    request: Request,
    hours: Annotated[int, Query(ge=1, le=24 * 90)] = 24,
    provider: Annotated[Literal["claude", "codex"] | None, Query()] = None,
) -> HistoryResponse:
    store: SnapshotStore | None = request.app.state.store
    series = store.history(hours=hours, provider=provider) if store else []
    return HistoryResponse(since=now() - timedelta(hours=hours), series=series)


@router.get("/logs/summary", response_model=LogSummary, summary="Verbrauch aus JSONL-Logs")
async def read_log_summary(
    request: Request,
    days: Annotated[int, Query(ge=1, le=365)] = 7,
    group_by: Annotated[
        Literal["day", "project", "model", "provider"], Query()
    ] = "day",
) -> LogSummary:
    store: LogStore = request.app.state.logs
    return await anyio.to_thread.run_sync(
        lambda: store.summary(days=days, group_by=group_by)
    )


@router.get("/health", response_model=HealthResponse, summary="Dienststatus")
async def read_health(request: Request) -> HealthResponse:
    settings = _settings(request)
    poller = _poller(request)

    return HealthResponse(
        status="ok",
        version=__version__,
        demo_mode=settings.demo_mode,
        loopback_only=settings.binds_loopback_only,
        history_enabled=bool(request.app.state.store),
        last_poll_at=poller.last_poll_at,
        last_poll_error=poller.last_error,
        sources={
            "claude_credentials": settings.claude_credentials_path.exists(),
            "claude_logs": settings.claude_projects_dir.is_dir(),
            "codex_credentials": settings.codex_auth_path.exists(),
            "codex_logs": settings.codex_sessions_dir.is_dir(),
        },
    )
