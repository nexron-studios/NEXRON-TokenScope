from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Annotated, Literal

import anyio.to_thread
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

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

#: Abstand zwischen zwei Lebenszeichen im Datenstrom. Ohne sie merkt keine der
#: beiden Seiten, dass die andere weg ist – die Verbindung bliebe als Leiche
#: offen.
STREAM_HEARTBEAT_SECONDS = 20.0


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


def _as_event(snapshot: UsageResponse) -> str:
    return f"data: {snapshot.model_dump_json()}\n\n"


@router.get("/events", summary="Kontingente als Datenstrom")
async def stream_usage(request: Request) -> StreamingResponse:
    """Schickt jeden neuen Stand, sobald er da ist.

    Vorher kannte die Oberfläche nur ihr eigenes Intervall: Nach einem
    erneuerten Token blieb die Kachel bis zu eine Minute auf dem alten Wert
    stehen, und nur der Aktualisieren-Knopf half. Kein ``response_model`` –
    der Rumpf ist ein Ereignisstrom, kein einzelnes Objekt.
    """
    poller = _poller(request)

    async def events() -> AsyncIterator[str]:
        with poller.subscribe() as stream:
            # Der erste Push ist der aktuelle Stand. Damit ist auch jede
            # Neuverbindung sofort wieder auf dem Laufenden.
            yield _as_event(poller.snapshot)

            while True:
                try:
                    snapshot = await asyncio.wait_for(
                        stream.get(), STREAM_HEARTBEAT_SECONDS
                    )
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue

                if snapshot is None:
                    return
                yield _as_event(snapshot)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


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
