from __future__ import annotations

import math
from datetime import timedelta

import httpx

from ..models import ProviderId, ProviderUsage, UsageWindow
from ..normalize import clamp_percent, now


class DemoProvider:
    """Erzeugt plausible Werte ohne Credentials.

    Nur für UI-Arbeit gedacht (``AIUSAGE_DEMO_MODE=1``). Das Frontend
    kennzeichnet diese Quelle sichtbar als Demo.
    """

    def __init__(self, provider_id: ProviderId, name: str, plan: str) -> None:
        self.id = provider_id
        self.name = name
        self._plan = plan

    async def fetch(self, client: httpx.AsyncClient) -> ProviderUsage:
        moment = now()
        phase = moment.timestamp() / 900.0
        offset = 0.0 if self.id == "claude" else 1.7

        short = clamp_percent(46 + 34 * math.sin(phase + offset))
        long = clamp_percent(58 + 12 * math.sin(phase / 6 + offset))

        return ProviderUsage(
            id=self.id,
            name=self.name,
            plan=self._plan,
            source="demo",
            status="ok",
            message="Simulierte Werte – keine echten Kontingente.",
            fetched_at=moment,
            windows=[
                UsageWindow(
                    key="five_hour",
                    label="5 Stunden",
                    used_percent=short,
                    remaining_percent=clamp_percent(100 - short),
                    resets_at=moment + timedelta(hours=2, minutes=18),
                    window_minutes=300,
                    primary=True,
                ),
                UsageWindow(
                    key="seven_day",
                    label="7 Tage",
                    used_percent=long,
                    remaining_percent=clamp_percent(100 - long),
                    resets_at=moment + timedelta(days=3, hours=5),
                    window_minutes=10080,
                ),
            ],
        )
