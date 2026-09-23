"""Wetter für die Kopfzeile: Standort über die IP, Werte von Open-Meteo.

Das ist die einzige Stelle, an der TokenScope einen Dienst kontaktiert, der
nichts mit dem Kontingent zu tun hat. Deshalb bleibt sie eng gefasst: zwei
Anbieter ohne Schlüssel, ein Zwischenspeicher, und ein Schalter, der alles
abstellt (``weather_enabled``).

Der Standort kommt aus der öffentlichen IP – das ist stadtgenau und genügt
fürs Wetter, kostet aber keine Rückfrage beim Nutzer, wie es die
Browser-Ortung täte. Wer woanders wohnt als seine IP behauptet, trägt in
``weather_place`` samt Koordinaten seinen Ort ein; dann wird gar nicht erst
geortet.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx

from .config import Settings
from .models import WeatherReport
from .normalize import now, parse_timestamp

logger = logging.getLogger(__name__)

_USER_AGENT = "nexron-tokenscope/0.2 (local dashboard)"

#: Die IP wechselt selten, der Ort noch seltener – einmal am Tag genügt.
LOCATION_TTL = timedelta(hours=12)

#: Open-Meteo rechnet in 15-Minuten-Schritten. Öfter zu fragen bringt
#: denselben Wert zurück.
MINIMUM_WEATHER_TTL_SECONDS = 600


@dataclass(frozen=True)
class Location:
    """Wo gefragt wird. ``label`` ist, was in der Kopfzeile steht."""

    latitude: float
    longitude: float
    label: str


class WeatherError(RuntimeError):
    """Abruf gescheitert – die Kachel bleibt dann einfach leer."""


class WeatherService:
    """Hält den letzten Wetterbericht und erneuert ihn nach Ablauf.

    Jeder Fehler bleibt hier: Der Aufrufer bekommt ``None`` und zeigt nichts
    an. Ein ausgefallener Wetterdienst darf das Dashboard nicht beschädigen –
    er hat mit dessen eigentlicher Aufgabe nichts zu tun.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._location: Location | None = None
        self._located_at: datetime | None = None
        self._report: WeatherReport | None = None
        self._fetched_at: datetime | None = None

    async def report(self) -> WeatherReport | None:
        settings = self._settings
        if not settings.weather_enabled:
            return None

        ttl = max(settings.weather_ttl_seconds, MINIMUM_WEATHER_TTL_SECONDS)
        if self._report is not None and self._fetched_at is not None:
            if (now() - self._fetched_at).total_seconds() < ttl:
                return self._report

        try:
            # Ein eigener, kurzlebiger Client: Der Abruf läuft höchstens alle
            # 15 Minuten, da wiegt ein dauerhaft offener Verbindungspool mehr
            # als er spart – und der Poller behält seinen für sich.
            async with httpx.AsyncClient(
                timeout=10.0, headers={"User-Agent": _USER_AGENT}
            ) as client:
                location = await self._locate(client)
                self._report = await self._fetch(client, location)
            self._fetched_at = now()
        except (WeatherError, httpx.HTTPError) as exc:
            # Der alte Bericht bleibt stehen, solange es einen gibt: ein
            # zehn Minuten alter Wert ist brauchbarer als eine leere Zeile.
            logger.warning("weather.refresh_failed: %s", exc)

        return self._report

    # --- Standort ---------------------------------------------------------

    async def _locate(self, client: httpx.AsyncClient) -> Location:
        settings = self._settings
        if settings.weather_latitude is not None and settings.weather_longitude is not None:
            return Location(
                latitude=settings.weather_latitude,
                longitude=settings.weather_longitude,
                label=settings.weather_place or "",
            )

        if self._location is not None and self._located_at is not None:
            if now() - self._located_at < LOCATION_TTL:
                return self._location

        response = await client.get(settings.weather_location_url, timeout=10.0)
        if response.status_code != 200:
            raise WeatherError(f"Ortung antwortete mit HTTP {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise WeatherError("Ortung lieferte kein JSON") from exc

        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            raise WeatherError("Ortung ohne Koordinaten")

        city = payload.get("city")
        self._location = Location(
            latitude=float(latitude),
            longitude=float(longitude),
            label=str(city) if city else "",
        )
        self._located_at = now()
        logger.info("weather.located: %s", self._location.label or "unbenannt")
        return self._location

    # --- Wetter -----------------------------------------------------------

    async def _fetch(
        self, client: httpx.AsyncClient, location: Location
    ) -> WeatherReport:
        response = await client.get(
            self._settings.weather_forecast_url,
            params={
                "latitude": location.latitude,
                "longitude": location.longitude,
                "current": "temperature_2m,apparent_temperature,is_day,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
                "forecast_days": 1,
            },
            timeout=10.0,
        )
        if response.status_code != 200:
            raise WeatherError(f"Wetterdienst antwortete mit HTTP {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise WeatherError("Wetterdienst lieferte kein JSON") from exc

        return build_report(payload, place=location.label)


def _first(payload: dict, key: str) -> float | None:
    """Holt den ersten Tageswert – angefragt ist genau einer."""
    values = payload.get(key)
    if not isinstance(values, list) or not values:
        return None
    value = values[0]
    return float(value) if isinstance(value, (int, float)) else None


def build_report(payload: object, *, place: str) -> WeatherReport:
    """Formt die Open-Meteo-Antwort in unser Schema.

    Ohne aktuelle Temperatur hat die Anzeige keinen Inhalt – dann lieber ein
    Fehler als eine Kachel, die einen Strich zeigt.
    """
    if not isinstance(payload, dict):
        raise WeatherError("Unerwartete Antwortform")

    current = payload.get("current")
    if not isinstance(current, dict):
        raise WeatherError("Antwort ohne aktuellen Messwert")

    temperature = current.get("temperature_2m")
    if not isinstance(temperature, (int, float)):
        raise WeatherError("Antwort ohne Temperatur")

    daily = payload.get("daily") if isinstance(payload.get("daily"), dict) else {}
    feels_like = current.get("apparent_temperature")
    code = current.get("weather_code")

    # `timezone=auto` liefert Ortszeit ohne Zeitzonenangabe – ungerechnet wäre
    # der Messzeitpunkt im Sommer zwei Stunden in der Zukunft. Die Tageswerte
    # brauchen den lokalen Tag, deshalb wird umgerechnet statt in UTC gefragt.
    offset = payload.get("utc_offset_seconds")
    observed_at = parse_timestamp(current.get("time"))
    if observed_at is not None and isinstance(offset, (int, float)):
        observed_at -= timedelta(seconds=float(offset))

    return WeatherReport(
        place=place,
        temperature=round(float(temperature), 1),
        feels_like=round(float(feels_like), 1)
        if isinstance(feels_like, (int, float))
        else None,
        day_high=_first(daily, "temperature_2m_max"),
        day_low=_first(daily, "temperature_2m_min"),
        weather_code=int(code) if isinstance(code, (int, float)) else 0,
        is_day=bool(current.get("is_day", 1)),
        observed_at=observed_at or now(),
    )
