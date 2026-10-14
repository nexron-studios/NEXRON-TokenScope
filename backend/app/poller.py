from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from datetime import datetime, timedelta

import httpx

from .claude_accounts import ClaudeAccount, discover_claude_accounts
from .cli_refresh import CliRefresher
from .config import Settings
from .models import AccountInfo, ProviderUsage, UsageResponse
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

#: Ein Abonnent will den letzten Stand, nicht jeden verpassten Zwischenschritt –
#: deshalb fasst seine Schlange genau einen Eintrag.
STREAM_QUEUE_SIZE = 1

#: Was ein Datenstrom bekommt: den neuen Stand, oder ``None`` als Schlusszeichen
#: beim Herunterfahren.
StreamQueue = asyncio.Queue["UsageResponse | None"]


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
    return "; ".join(f"{_display_name(item)}: {reason}" for item, reason in troubled)


def _display_name(item: ProviderUsage) -> str:
    return f"{item.name} ({item.account.name})" if item.account else item.name


def _is_auth_expired(item: ProviderUsage) -> bool:
    """Ob dieser Anbieter an einem abgelaufenen Token hängt.

    Nach dem Überbrücken trägt die Kachel den letzten guten Wert und den Grund
    nur noch in ``warning_status`` – beide Stellen müssen also gelesen werden.
    """
    return "auth_expired" in (item.status, item.warning_status)


def build_providers(settings: Settings, accounts: list[ClaudeAccount]) -> list[Provider]:
    if settings.demo_mode:
        # Zwei Claude-Logins, damit die Mehr-Account-Ansicht ohne echte
        # Anmeldungen entworfen werden kann.
        return [
            DemoProvider(
                "claude",
                "Claude Code",
                "Max",
                AccountInfo(id="demo-private", name="privat", email="privat@example.com"),
            ),
            DemoProvider(
                "claude",
                "Claude Code",
                "Pro",
                AccountInfo(id="demo-work", name="arbeit", email="arbeit@example.com"),
                offset=0.9,
            ),
            DemoProvider("codex", "Codex", "Plus", offset=1.7),
        ]

    providers: list[Provider] = []
    if settings.claude_enabled:
        providers.extend(ClaudeProvider(settings, account) for account in accounts)
    if settings.codex_enabled:
        providers.append(CodexProvider(settings))
    return providers


class UsagePoller:
    """Fragt beide Quellen periodisch ab und hält das Ergebnis im Cache.

    Jede Anbieterabfrage ist einzeln abgesichert: Ein kaputter Endpunkt leert
    genau eine Kachel, nie das ganze Dashboard.
    """

    def __init__(
        self,
        settings: Settings,
        store: SnapshotStore | None = None,
        accounts: list[ClaudeAccount] | None = None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._accounts = (
            discover_claude_accounts(settings) if accounts is None else accounts
        )
        self._providers = build_providers(settings, self._accounts)
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
        #: Offene Datenströme, die auf den nächsten Stand warten.
        self._subscribers: set[StreamQueue] = set()

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
        # Erst die Ströme verabschieden: Ohne Schlusszeichen wartet uvicorn beim
        # Herunterfahren auf eine Verbindung, die von sich aus nie endet.
        for queue in list(self._subscribers):
            self._offer(queue, None)

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
            if self._accounts and not self._settings.demo_mode:
                adopted = store.adopt_legacy("claude", self._accounts[0].info.id)
                if adopted:
                    logger.info(
                        "%d ältere Messpunkte dem Login %s zugeordnet",
                        adopted,
                        self._accounts[0].info.name,
                    )
            # Der letzte echte Messwert bleibt als klar markierter Altstand
            # nützlicher als eine leere Kachel, auch wenn er lange zurückliegt.
            restored = store.latest_per_provider()
        except Exception:  # pragma: no cover - Start darf daran nie scheitern
            logger.exception("Letzter Stand konnte nicht geladen werden")
            return

        # Nur Logins, die es noch gibt – und mit ihrem aktuellen Namen statt
        # der bloßen ID aus der Datenbank.
        by_key = {provider.key: provider for provider in self._providers}
        for entry in restored:
            provider = by_key.get(entry.key)
            if provider is None:
                continue
            self._last_good[entry.key] = self._own(provider, entry)
        if self._last_good:
            logger.info(
                "Letzter Stand für %s wiederhergestellt",
                ", ".join(_display_name(entry) for entry in self._last_good.values()),
            )

    def _credential_stamp(self) -> tuple[float | None, ...]:
        """Änderungszeiten der Claude-Credentials, sofern es sie als Datei gibt.

        Auf macOS liegt der Token im Keychain – dort gibt es nichts zu
        beobachten und es bleibt beim Intervall.
        """
        stamps: list[float | None] = []
        for account in self._accounts:
            for path in account.credential_paths:
                try:
                    stamps.append(path.stat().st_mtime)
                except OSError:
                    stamps.append(None)
        return tuple(stamps)

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
            if current != stamp:
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

    # --- Datenstrom -------------------------------------------------------

    @contextmanager
    def subscribe(self) -> Iterator[StreamQueue]:
        """Meldet einen Datenstrom an, der auf jede Änderung wartet.

        Ohne das kennt die Oberfläche nur ihr eigenes Intervall: Zwischen einem
        erneuerten Token und der sichtbaren Kachel lag bis zu eine Minute, in
        der nur der Aktualisieren-Knopf half.
        """
        queue: StreamQueue = asyncio.Queue(maxsize=STREAM_QUEUE_SIZE)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)

    def _offer(self, queue: StreamQueue, value: UsageResponse | None) -> None:
        """Legt den neuen Stand hin und wirft den überholten weg.

        Die Schlange fasst genau einen Eintrag – ein Abonnent, der noch nicht
        abgeholt hat, soll den aktuellen Stand bekommen, keine Warteschlange
        veralteter Zwischenstände.
        """
        # Leer heißt hier: der Abonnent war schneller. Das ist der Normalfall.
        with suppress(asyncio.QueueEmpty):
            queue.get_nowait()
        queue.put_nowait(value)

    def _publish(self) -> None:
        for queue in self._subscribers:
            self._offer(queue, self._snapshot)

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
            self._publish()

        # Erst außerhalb des Locks: Der Anstoß fragt den Anbieter danach selbst
        # noch einmal ab und braucht das Lock dafür.
        self._schedule_renewals(results)
        return self._snapshot

    @staticmethod
    def _own(provider: Provider, result: ProviderUsage) -> ProviderUsage:
        """Schreibt den Login an das Ergebnis – die Provider kennen nur ihren Abruf."""
        return result.model_copy(update={"account": provider.account})

    async def _fetch_one(self, provider: Provider) -> ProviderUsage:
        cooldown = self._cooldown_until.get(provider.key)
        if cooldown is not None:
            remaining = (cooldown - now()).total_seconds()
            if remaining > 0:
                wait = (
                    f"{int(remaining)} s"
                    if remaining < 90
                    else f"{round(remaining / 60)} min"
                )
                return self._bridge(
                    self._own(
                        provider,
                        build_error(
                            provider.id,
                            provider.name,
                            "rate_limited",
                            f"Drosselung, neuer Versuch in {wait}",
                            retry_after_seconds=remaining,
                        ),
                    )
                )
            del self._cooldown_until[provider.key]

        if self._client is None:
            return self._bridge(
                self._own(
                    provider,
                    build_error(
                        provider.id, provider.name, "error", "HTTP-Client nicht bereit."
                    ),
                )
            )

        try:
            result = await provider.fetch(self._client)
        except Exception as exc:  # pragma: no cover - letzte Verteidigungslinie
            logger.exception("Provider %s ist unerwartet gescheitert", provider.key)
            result = build_error(
                provider.id,
                provider.name,
                "error",
                f"Unerwarteter Fehler: {exc.__class__.__name__}",
            )
        result = self._own(provider, result)

        if result.status == "ok":
            self._last_good[provider.key] = result
            return result

        self._arm_cooldown(result)
        return self._bridge(result)

    def _arm_cooldown(self, failure: ProviderUsage) -> None:
        """Pausiert einen gedrosselten Anbieter, statt stur weiterzupollen."""
        if failure.status != "rate_limited":
            return

        wait = failure.retry_after_seconds or DEFAULT_RATE_LIMIT_COOLDOWN
        wait = min(max(wait, self._settings.poll_interval_seconds), MAX_COOLDOWN)
        self._cooldown_until[failure.key] = now() + timedelta(seconds=wait)
        logger.warning(
            "%s ist ratenbegrenzt – pausiere %d s", _display_name(failure), int(wait)
        )

    def _bridge(self, failure: ProviderUsage) -> ProviderUsage:
        """Zeigt bei einem Aussetzer dauerhaft den letzten echten Abruf.

        Der Wert bleibt mitsamt seinem ursprünglichen Zeitstempel erhalten und
        ist als ``stale`` markiert. So kann die Oberfläche ihn als historischen
        Stand darstellen, statt bei einem abgelaufenen Token leer zu werden.
        """
        previous = self._last_good.get(failure.key)
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
            if not self._refresher.may_attempt(item.key):
                continue

            task = asyncio.create_task(
                self._renew(item.key), name=f"cli-refresh-{item.key}"
            )
            self._renewals.add(task)
            task.add_done_callback(self._renewals.discard)

    async def _renew(self, key: str) -> None:
        provider = next((p for p in self._providers if p.key == key), None)
        if provider is None:
            return

        try:
            if not await self._refresher.trigger(key, provider.refresh_env):
                return

            # Ob das Kommando den Token wirklich erneuert hat, entscheidet der
            # nächste Abruf – nicht sein Rückgabewert.
            async with self._lock:
                result = await self._fetch_one(provider)
                self._apply_renewal(result)
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover - darf den Poller nie beschädigen
            logger.exception("CLI-Anstoß für %s fehlgeschlagen", key)
            return

        if result.status == "ok" and not result.stale:
            logger.info("cli.refresh_recovered: %s liefert wieder Werte", key)
            return

        logger.warning(
            "cli.refresh_ineffective: %s bleibt auf %s – erneuert das Kommando "
            "den Token überhaupt?",
            key,
            result.warning_status or result.status,
        )

    def _apply_renewal(self, result: ProviderUsage) -> None:
        """Tauscht eine einzelne Kachel im aktuellen Snapshot aus."""
        moment = now()
        providers = [
            result if item.key == result.key else item
            for item in self._snapshot.providers
        ]
        self._snapshot = self._snapshot.model_copy(
            update={"generated_at": moment, "providers": providers}
        )
        self._last_error = _describe_trouble(providers)
        self._persist(moment, [result])
        self._publish()

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
