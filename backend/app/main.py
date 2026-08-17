from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .api import router
from .config import Settings, get_settings
from .logs import LogStore
from .poller import UsagePoller
from .storage import SnapshotStore

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings

    if not settings.binds_loopback_only:
        logger.warning(
            "Der Dienst lauscht auf %s statt auf 127.0.0.1. Die gelesenen Tokens "
            "sind vollwertige Account-Credentials – nicht ins Netz stellen.",
            settings.host,
        )

    store: SnapshotStore | None = None
    if settings.history_enabled:
        store = SnapshotStore(settings.database_path, settings.history_retention_days)
        try:
            store.connect()
        except Exception:
            logger.exception("SQLite nicht verfügbar – Historie bleibt aus")
            store = None
    app.state.store = store

    app.state.logs = LogStore(settings)

    poller = UsagePoller(settings, store)
    app.state.poller = poller
    await poller.start()

    logger.info(
        "Bereit auf http://%s:%d (Demo-Modus: %s, Historie: %s)",
        settings.host,
        settings.port,
        "an" if settings.demo_mode else "aus",
        "an" if store else "aus",
    )

    try:
        yield
    finally:
        await poller.stop()
        if store is not None:
            store.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    _configure_logging()
    resolved = settings or get_settings()

    app = FastAPI(
        title="NEXRON-TokenScope",
        description=(
            "Lokaler Dienst, der die Kontingente von Claude Code und Codex "
            "aus den Dateien der jeweiligen CLI liest und normalisiert ausliefert."
        ),
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = resolved

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def disable_api_cache(request: Request, call_next):
        """API-Antworten enthalten Live-Daten und duerfen nie im WebView-Cache landen."""
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    app.include_router(router)

    dist = resolved.frontend_dist
    if (dist / "index.html").is_file():
        if (dist / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{_path:path}", include_in_schema=False)
        async def serve_spa(_path: str) -> FileResponse:
            return FileResponse(dist / "index.html")

    return app


app = create_app()


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
