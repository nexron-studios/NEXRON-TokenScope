from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

import httpx

from .cli_refresh import CliRefresher
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

#: Taktung, in der zwischen zwei Polls auf erneuerte Credentials geschaut wird.
CREDENTIAL_WATCH_SECONDS = 2.0


def _describe_trouble(results: list[ProviderUsage]) -> str | None:
    """Fasst zusammen, was schiefging – für ``/api/health``.

    Auch überbrückte Anbieter melden hier ihren Grund: Die Kachel zeigt zwar
    Werte, der frische Abruf ist aber trotzdem gescheitert.
    """
    troubled = [
        (item, item.message if item.status != "ok" else item.warning)
        for item in results
        if item.status != "ok" or item.stale
    ]
    if not troubled:
        return None
    return "; ".join(f"{item.name}: {reason}" for item, reason in troubled)


def _is_auth_expired(item: ProviderUsage) -> bool:
    """Ob dieser Anbieter an einem abgelaufenen Token hängt.

    Nach dem Überbrücken trägt die Kachel den letzten guten Wert und den Grund
    nur noch in ``warning_status`` – beide Stellen müssen also gelesen werden.
    """
    return "auth_expired" in (item.status, item.warning_status)


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
        self._refresher = CliRefresher(settings)
        #: Laufende CLI-Anstöße – ohne Referenz sammelt der GC sie wieder ein.
        self._renewals: set[asyncio.Task[None]] = set()
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
        for renewal in list(self._renewals):
            renewal.cancel()
        self._renewals.clear()
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

    def _credential_stamp(self) -> float | None:
        """Änderungszeit der Claude-Credentials, sofern es sie als Datei gibt.

        Auf macOS liegt der Token im Keychain – dort gibt es nichts zu
        beobachten und es bleibt beim Intervall.
        """
        try:
            return self._settings.claude_credentials_path.stat().st_mtime
        except OSError:
            return None

    async def _sleep_until_due(self, interval: int) -> None:
        """Wartet das Intervall ab – oder bis die CLI den Token erneuert hat.

        Ohne das läge ein frisch geschriebener Token bis zu eine Minute
        ungenutzt herum, während die Kachel weiter „abgelaufen" zeigt.
        """
        stamp = self._credential_stamp()
        waited = 0.0
        while waited < interval:
            step = min(CREDENTIAL_WATCH_SECONDS, interval - waited)
            await asyncio.sleep(step)
            waited += step

            current = self._credential_stamp()
            if current is not None and current != stamp:
                logger.info("credentials.changed: hole sofort neu")
                return

    async def _loop(self) -> None:
        interval = max(10, self._settings.poll_interval_seconds)
        while True:
            try:
                await self._sleep_until_due(interval)
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
            self._last_error = _describe_trouble(results)

            self._persist(moment, results)

        # Erst außerhalb des Locks: Der Anstoß fragt den Anbieter danach selbst
        # noch einmal ab und braucht das Lock dafür.
        self._schedule_renewals(results)
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

    # --- Token-Erneuerung -------------------------------------------------

    def _schedule_renewals(self, results: list[ProviderUsage]) -> None:
        """Lässt für jeden abgelaufenen Token die zugehörige CLI anstoßen.

        Im Hintergrund, damit ein ``?refresh=true`` aus der Oberfläche nicht auf
        ein fremdes Kommando wartet.
        """
        for item in results:
            if not _is_auth_expired(item):
                continue
            if not self._refresher.may_attempt(item.id):
                continue

            task = asyncio.create_task(
                self._renew(item.id), name=f"cli-refresh-{item.id}"
            )
            self._renewals.add(task)
            task.add_done_callback(self._renewals.discard)

    async def _renew(self, provider_id: str) -> None:
        provider = next((p for p in self._providers if p.id == provider_id), None)
        if provider is None:
            return

        try:
            if not await self._refresher.trigger(provider_id):
                return

            # Ob das Kommando den Token wirklich erneuert hat, entscheidet der
            # nächste Abruf – nicht sein Rückgabewert.
            async with self._lock:
                result = await self._fetch_one(provider)
                self._apply_renewal(result)
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover - darf den Poller nie beschädigen
            logger.exception("CLI-Anstoß für %s fehlgeschlagen", provider_id)
            return

        if result.status == "ok" and not result.stale:
            logger.info("cli.refresh_recovered: %s liefert wieder Werte", provider_id)
            return

        logger.warning(
            "cli.refresh_ineffective: %s bleibt auf %s – erneuert das Kommando "
            "den Token überhaupt?",
            provider_id,
            result.warning_status or result.status,
        )

    def _apply_renewal(self, result: ProviderUsage) -> None:
        """Tauscht eine einzelne Kachel im aktuellen Snapshot aus."""
        moment = now()
        providers = [
            result if item.id == result.id else item
            for item in self._snapshot.providers
        ]
        self._snapshot = self._snapshot.model_copy(
            update={"generated_at": moment, "providers": providers}
        )
        self._last_error = _describe_trouble(providers)
        self._persist(moment, [result])

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
