"""Lage der Anbieter-Statusseiten – ob Claude oder Codex selbst gestört ist.

Ohne diese Angabe sieht ein Ausfall beim Anbieter auf dem Dashboard aus wie ein
Fehler hier: Die Kachel hält ihren letzten Wert, der Abruf scheitert, und
niemand weiß, auf welcher Seite das Problem liegt.

Beide Seiten sprechen das Statuspage-Format (``summary.json`` und
``incidents.json``, ohne Schlüssel), unterscheiden sich aber darin, was sie
mitliefern:

- **status.claude.com** hängt jeder Störung ihre Komponenten an. Relevant ist,
  was Claude Code, die API oder claude.ai betrifft.
- **status.openai.com** (incident.io mit Statuspage-Kompatibilität) liefert
  Störungen ohne Komponenten und ohne Kurzlink, und die Seite handelt zum
  größten Teil von ChatGPT. Relevant ist dort nur, was Codex im Titel nennt –
  sonst stünde jede ChatGPT-Störung auf der Codex-Seite.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx

from .config import Settings
from .models import (
    ProviderId,
    ServiceComponent,
    ServiceIncident,
    ServiceLevel,
    ServiceMaintenance,
    ServiceStatus,
)
from .normalize import now, parse_timestamp

logger = logging.getLogger(__name__)

_USER_AGENT = "nexron-tokenscope/0.2 (local dashboard)"

#: Unter einer Minute zu fragen bringt nichts – die Statusseiten werden von
#: Menschen gepflegt, nicht von Messpunkten.
MINIMUM_TTL_SECONDS = 20

#: Während einer Störung ändert sich die Seite im Minutentakt, und „behoben"
#: ist genau die Meldung, die man früh sehen will.
INCIDENT_TTL_SECONDS = 20

#: Solange ein gescheiterter Abruf jünger ist, gilt der alte Stand weiter als
#: aktuell. Danach sagt er nichts mehr über jetzt und wird als veraltet markiert.
STALE_AFTER = timedelta(minutes=10)

RECENTLY_RESOLVED = timedelta(minutes=45)
MAINTENANCE_LOOKAHEAD = timedelta(hours=6)

_COMPONENT_LEVEL: dict[str, ServiceLevel] = {
    "operational": "ok",
    "under_maintenance": "maintenance",
    "degraded_performance": "degraded",
    "partial_outage": "outage",
    "major_outage": "outage",
}

_IMPACT_LEVEL: dict[str, ServiceLevel] = {
    "none": "degraded",
    "minor": "degraded",
    "major": "outage",
    "critical": "outage",
}

_LEVEL_RANK: dict[ServiceLevel, int] = {"ok": 0, "maintenance": 1, "degraded": 2, "outage": 3}


@dataclass(frozen=True)
class StatusSource:
    """Was von einer Statusseite für einen Anbieter zählt."""

    provider: ProviderId
    page_url: str
    #: Komponenten, von denen das Arbeiten hier abhängt.
    components: re.Pattern[str]
    #: Titel, die eine Störung ohne passende Komponente relevant machen.
    #: ``None`` heißt: Eine Störung ganz ohne Komponenten zählt immer, weil die
    #: Seite sie oft eröffnet, bevor jemand eingetragen hat, was sie betrifft.
    incident_names: re.Pattern[str] | None = None
    #: Für Seiten ohne Kurzlink – ``{id}`` ist die Kennung der Störung.
    incident_url: str | None = None


CLAUDE = StatusSource(
    provider="claude",
    page_url="https://status.claude.com",
    components=re.compile(r"claude code|claude api|^claude\.ai$", re.IGNORECASE),
)

CODEX = StatusSource(
    provider="codex",
    page_url="https://status.openai.com",
    # „CLI" ist Codex im Terminal, „Login" die Anmeldung über das ChatGPT-Konto,
    # an der auch Codex hängt. Conversations, GPTs & Co. sind reines ChatGPT.
    components=re.compile(r"^(cli|login)$", re.IGNORECASE),
    incident_names=re.compile(r"codex|\bcli\b|log ?in|sign-?in", re.IGNORECASE),
    incident_url="https://status.openai.com/incidents/{id}",
)


class ServiceStatusError(RuntimeError):
    """Abruf gescheitert – der letzte gute Stand bleibt stehen."""


def _short_name(name: str) -> str:
    """„Claude API (api.anthropic.com)" → „Claude API"."""
    return re.sub(r"\s*\(.*\)$", "", name)


def _incident_url(raw: dict, source: StatusSource) -> str:
    if isinstance(raw.get("shortlink"), str):
        return raw["shortlink"]
    if source.incident_url and raw.get("id"):
        return source.incident_url.format(id=raw["id"])
    return source.page_url


def _incident(raw: dict, source: StatusSource) -> ServiceIncident | None:
    started_at = parse_timestamp(raw.get("created_at"))
    name = raw.get("name")
    if started_at is None or not isinstance(name, str):
        return None

    components = [
        _short_name(component["name"])
        for component in raw.get("components") or []
        if isinstance(component, dict) and isinstance(component.get("name"), str)
    ]
    return ServiceIncident(
        name=name.strip(),
        status=str(raw.get("status") or "investigating"),
        impact=str(raw.get("impact") or "minor"),
        started_at=started_at,
        resolved_at=parse_timestamp(raw.get("resolved_at")),
        url=_incident_url(raw, source),
        components=components,
    )


def _touches_us(incident: ServiceIncident, source: StatusSource) -> bool:
    if any(source.components.search(name) for name in incident.components):
        return True
    if source.incident_names is not None:
        return bool(source.incident_names.search(incident.name))
    return not incident.components


def _components(summary: dict, source: StatusSource) -> list[ServiceComponent]:
    return [
        ServiceComponent(name=_short_name(raw["name"]), status=raw["status"])
        for raw in summary.get("components") or []
        if isinstance(raw, dict)
        and isinstance(raw.get("name"), str)
        and source.components.search(raw["name"])
        and raw.get("status") in _COMPONENT_LEVEL
    ]


def _maintenance(summary: dict, at: datetime) -> ServiceMaintenance | None:
    for raw in summary.get("scheduled_maintenances") or []:
        scheduled_for = parse_timestamp(raw.get("scheduled_for"))
        if scheduled_for is None:
            continue
        status = str(raw.get("status") or "scheduled")
        upcoming = timedelta(0) < scheduled_for - at < MAINTENANCE_LOOKAHEAD
        if status == "in_progress" or upcoming:
            return ServiceMaintenance(
                name=str(raw.get("name") or ""), status=status, scheduled_for=scheduled_for
            )
    return None


def _recently_resolved(
    history: list, source: StatusSource, at: datetime
) -> ServiceIncident | None:
    for raw in history:
        incident = _incident(raw, source) if isinstance(raw, dict) else None
        if incident is None or incident.resolved_at is None:
            continue
        if not _touches_us(incident, source):
            continue
        if at - incident.resolved_at < RECENTLY_RESOLVED:
            return incident
    return None


def _open_incidents(summary: dict, source: StatusSource) -> list[ServiceIncident]:
    incidents = [
        _incident(raw, source) for raw in summary.get("incidents") or [] if isinstance(raw, dict)
    ]
    return [
        incident
        for incident in incidents
        if incident is not None
        and incident.status != "resolved"
        and _touches_us(incident, source)
    ]


def _level(
    components: list[ServiceComponent],
    incidents: list[ServiceIncident],
    maintenance: ServiceMaintenance | None,
) -> ServiceLevel:
    levels: list[ServiceLevel] = [_COMPONENT_LEVEL[c.status] for c in components]
    levels += [_IMPACT_LEVEL.get(i.impact, "degraded") for i in incidents]
    if maintenance is not None and maintenance.status == "in_progress":
        levels.append("maintenance")
    return max(levels, key=_LEVEL_RANK.__getitem__, default="ok")


def build_status(
    summary: object, history: object, *, source: StatusSource, at: datetime
) -> ServiceStatus:
    """Formt die beiden Statuspage-Antworten in unser Schema."""
    if not isinstance(summary, dict) or not isinstance(summary.get("components"), list):
        raise ServiceStatusError(f"Unerwartete Antwortform von {source.page_url}")

    incidents = _open_incidents(summary, source)
    components = _components(summary, source)
    maintenance = _maintenance(summary, at)
    past = history.get("incidents") if isinstance(history, dict) else None

    return ServiceStatus(
        provider=source.provider,
        level=_level(components, incidents, maintenance),
        components=components,
        incidents=incidents,
        maintenance=maintenance,
        # Solange noch etwas offen ist, erklärt „eben behoben" nichts.
        recently_resolved=None if incidents else _recently_resolved(past or [], source, at),
        fetched_at=at,
        page_url=source.page_url,
    )


class _SourceCache:
    """Letzter Stand einer Statusseite samt Zeitpunkt der letzten Prüfung."""

    def __init__(self, source: StatusSource, summary_url: str, history_url: str) -> None:
        self.source = source
        self.summary_url = summary_url
        self.history_url = history_url
        self.status: ServiceStatus | None = None
        self.checked_at: datetime | None = None
        # Mehrere Browserfenster fragen gleichzeitig; nur eins soll ins Netz.
        self.lock = asyncio.Lock()


class ServiceStatusService:
    """Hält je Anbieter den letzten Stand und erneuert ihn nach Ablauf.

    Fehler bleiben hier. Ist eine Statusseite nicht erreichbar, gilt ihr alter
    Stand noch zehn Minuten; danach geht er als ``stale`` hinaus, damit die
    Oberfläche kein „alles in Ordnung" zeigt, das niemand mehr geprüft hat.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._caches = [
            _SourceCache(CLAUDE, settings.claude_status_url, settings.claude_status_history_url),
            _SourceCache(CODEX, settings.codex_status_url, settings.codex_status_history_url),
        ]

    async def statuses(self) -> list[ServiceStatus]:
        if not self._settings.service_status_enabled:
            return []

        async with httpx.AsyncClient(
            timeout=10.0, headers={"User-Agent": _USER_AGENT}
        ) as client:
            await asyncio.gather(*(self._refresh_if_due(cache, client) for cache in self._caches))
        return [cache.status for cache in self._caches if cache.status is not None]

    def _ttl_seconds(self, cache: _SourceCache) -> int:
        if cache.status is not None and cache.status.incidents:
            return INCIDENT_TTL_SECONDS
        return max(self._settings.service_status_ttl_seconds, MINIMUM_TTL_SECONDS)

    def _is_due(self, cache: _SourceCache) -> bool:
        if cache.checked_at is None:
            return True
        return (now() - cache.checked_at).total_seconds() >= self._ttl_seconds(cache)

    async def _refresh_if_due(self, cache: _SourceCache, client: httpx.AsyncClient) -> None:
        async with cache.lock:
            if not self._is_due(cache):
                return
            cache.checked_at = now()
            try:
                summary, history = await asyncio.gather(
                    self._get(client, cache.summary_url),
                    self._get(client, cache.history_url),
                )
                cache.status = build_status(summary, history, source=cache.source, at=now())
            except (ServiceStatusError, httpx.HTTPError) as exc:
                logger.warning(
                    "service_status.refresh_failed: %s %s", cache.source.provider, exc
                )
                self._mark_stale_if_old(cache)

    @staticmethod
    def _mark_stale_if_old(cache: _SourceCache) -> None:
        if cache.status is None:
            return
        if now() - cache.status.fetched_at > STALE_AFTER:
            cache.status = cache.status.model_copy(update={"stale": True})

    @staticmethod
    async def _get(client: httpx.AsyncClient, url: str) -> object:
        response = await client.get(url)
        if response.status_code != 200:
            raise ServiceStatusError(f"{url} antwortete mit HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise ServiceStatusError(f"{url} lieferte kein JSON") from exc
