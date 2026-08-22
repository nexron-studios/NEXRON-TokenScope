from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

import httpx

from .config import Settings
from .models import ProviderUsage, UsageResponse
from .normalize import now
from .providers import ClaudeProvider, CodexProvider, DemoProvider, Provider, build_error
from .storage import SnapshotStore

logger = logging.getLogger(__name__)

_USER_AGENT = "nexron-tokenscope/0.2 (local dashboard)"

#: Wartezeit, wenn der Anbieter drosselt, aber kein `Retry-After` mitschickt.
DEFAULT_RATE_LIMIT_COOLDOWN = 300.0
MAX_COOLDOWN = 1800.0


def build_providers(settings: Settings) -> list[Provider]:
    if settings.demo_mode:
        return [
            DemoProvider("claude", "Claude Code", "Max"),
            DemoProvider("codex", "Codex", "Plus"),
        ]

    providers: list[Provider] = []
    if settings.claude_enabled:
        providers.append(ClaudeProvider(settings))
    if settings.codex_enabled:
        providers.append(CodexProvider(settings))
    return providers


class UsagePoller:
    """Fragt beide Quellen periodisch ab und hält das Ergebnis im Cache.

    Jede Anbieterabfrage ist einzeln abgesichert: Ein kaputter Endpunkt leert
    genau eine Kachel, nie das ganze Dashboard.
    """

    def __init__(self, settings: Settings, store: SnapshotStore | None = None) -> None:
        self._settings = settings
        self._store = store
        self._providers = build_providers(settings)
        self._client: httpx.AsyncClient | None = None
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._snapshot = UsageResponse(
            generated_at=now(),
            poll_interval_seconds=settings.poll_interval_seconds,
            demo_mode=settings.demo_mode,
            providers=[],
        )
        self._last_success_at: datetime | None = None
        self._last_error: str | None = None
        self._last_prune_at: datetime | None = None
        #: Letzter geglückter Abruf je Anbieter – überbrückt Aussetzer.
        self._last_good: dict[str, ProviderUsage] = {}
        #: Bis dahin wird ein gedrosselter Anbieter gar nicht erst gefragt.
        self._cooldown_until: dict[str, datetime] = {}

    # --- Lebenszyklus -----------------------------------------------------

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=self._settings.request_timeout_seconds,
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=True,
        )
        self._restore_last_good()
        await self.refresh(force=True)
        self._task = asyncio.create_task(self._loop(), name="usage-poller")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _restore_last_good(self) -> None:
        """Holt den letzten gespeicherten Stand als Überbrückung zurück.

        Ohne das steht nach jedem Neustart wieder eine leere Kachel da, bis
        der erste Poll glückt – und gerade während einer Drosselung dauert
        das mehrere Minuten.
        """
        store = self._store
        if store is None or not store.is_open:
            return

        try:
            # Der letzte echte Messwert bleibt als klar markierter Altstand
            # nützlicher als eine leere Kachel, auch wenn er lange zurückliegt.
            restored = store.latest_per_provider()
        except Exception:  # pragma: no cover - Start darf daran nie scheitern
            logger.exception("Letzter Stand konnte nicht geladen werden")
            return

        for entry in restored:
            self._last_good[entry.id] = entry
        if restored:
            logger.info(
                "Letzter Stand für %s wiederhergestellt",
                ", ".join(entry.name for entry in restored),
            )

    async def _loop(self) -> None:
        interval = max(10, self._settings.poll_interval_seconds)
        while True:
            try:
                await asyncio.sleep(interval)
                await self.refresh(force=True)
            except asyncio.CancelledError:
                raise
            except Exception:  # pragma: no cover - Loop darf nie sterben
                logger.exception("Poll-Durchlauf fehlgeschlagen")

    # --- Abfrage ----------------------------------------------------------

    async def refresh(self, *, force: bool = False) -> UsageResponse:
        min_gap = self._settings.manual_refresh_min_interval_seconds
        if not force and self._last_success_at is not None:
            age = (now() - self._last_success_at).total_seconds()
            if age < min_gap:
                return self._snapshot

        async with self._lock:
            if not force and self._last_success_at is not None:
                age = (now() - self._last_success_at).total_seconds()
                if age < min_gap:
                    return self._snapshot

            results = await asyncio.gather(
                *(self._fetch_one(provider) for provider in self._providers)
            )

            moment = now()
            self._snapshot = UsageResponse(
                generated_at=moment,
                poll_interval_seconds=self._settings.poll_interval_seconds,
                demo_mode=self._settings.demo_mode,
                providers=list(results),
            )
            self._last_success_at = moment

            # Auch überbrückte Anbieter melden hier ihren Grund – die Kachel
            # zeigt zwar Werte, der Abruf ist aber trotzdem gescheitert.
            troubled = [
                (item, item.message if item.status != "ok" else item.warning)
                for item in results
                if item.status != "ok" or item.stale
            ]
            self._last_error = (
                "; ".join(f"{item.name}: {reason}" for item, reason in troubled)
                if troubled
                else None
            )

            self._persist(moment, results)
            return self._snapshot

    async def _fetch_one(self, provider: Provider) -> ProviderUsage:
        cooldown = self._cooldown_until.get(provider.id)
        if cooldown is not None:
            remaining = (cooldown - now()).total_seconds()
            if remaining > 0:
                wait = (
                    f"{int(remaining)} s"
                    if remaining < 90
                    else f"{round(remaining / 60)} min"
                )
                return self._bridge(
                    build_error(
                        provider.id,
                        provider.name,
                        "rate_limited",
                        f"Drosselung, neuer Versuch in {wait}",
                        retry_after_seconds=remaining,
                    )
                )
            del self._cooldown_until[provider.id]

        if self._client is None:
            return self._bridge(
                build_error(
                    provider.id, provider.name, "error", "HTTP-Client nicht bereit."
                )
            )

        try:
            result = await provider.fetch(self._client)
        except Exception as exc:  # pragma: no cover - letzte Verteidigungslinie
            logger.exception("Provider %s ist unerwartet gescheitert", provider.id)
            result = build_error(
                provider.id,
                provider.name,
                "error",
                f"Unerwarteter Fehler: {exc.__class__.__name__}",
            )

        if result.status == "ok":
            self._last_good[provider.id] = result
            return result

        self._arm_cooldown(result)
        return self._bridge(result)

    def _arm_cooldown(self, failure: ProviderUsage) -> None:
        """Pausiert einen gedrosselten Anbieter, statt stur weiterzupollen."""
        if failure.status != "rate_limited":
            return

        wait = failure.retry_after_seconds or DEFAULT_RATE_LIMIT_COOLDOWN
        wait = min(max(wait, self._settings.poll_interval_seconds), MAX_COOLDOWN)
        self._cooldown_until[failure.id] = now() + timedelta(seconds=wait)
        logger.warning(
            "%s ist ratenbegrenzt – pausiere %d s", failure.name, int(wait)
        )

    def _bridge(self, failure: ProviderUsage) -> ProviderUsage:
        """Zeigt bei einem Aussetzer dauerhaft den letzten echten Abruf.

        Der Wert bleibt mitsamt seinem ursprünglichen Zeitstempel erhalten und
        ist als ``stale`` markiert. So kann die Oberfläche ihn als historischen
        Stand darstellen, statt bei einem abgelaufenen Token leer zu werden.
        """
        previous = self._last_good.get(failure.id)
        if previous is None:
            return failure

        return previous.model_copy(
            update={
                "stale": True,
                "warning": failure.message,
                "warning_status": failure.status,
                "retry_after_seconds": failure.retry_after_seconds,
            }
        )

    def _persist(self, moment: datetime, results: list[ProviderUsage]) -> None:
        store = self._store
        if store is None or not store.is_open:
            return

        store.record(moment, results)

        if self._last_prune_at is None or moment - self._last_prune_at > timedelta(days=1):
            removed = store.prune()
            self._last_prune_at = moment
            if removed:
                logger.info("%d alte Snapshots entfernt", removed)

    # --- Status -----------------------------------------------------------

    @property
    def snapshot(self) -> UsageResponse:
        return self._snapshot

    @property
    def last_poll_at(self) -> datetime | None:
        return self._last_success_at

    @property
    def last_error(self) -> str | None:
        return self._last_error
