from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api import read_usage
from app.config import Settings
from app.main import create_app
from app.models import ProviderUsage, UsageWindow
from app.poller import UsagePoller
from app.providers.base import build_error
from app.storage import SnapshotStore


class _RecordingPoller:
    def __init__(self) -> None:
        self.force_values: list[bool] = []
        self.snapshot = object()

    async def refresh(self, *, force: bool = False):
        self.force_values.append(force)
        return self.snapshot


class RefreshApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_query_bypasses_manual_debounce(self) -> None:
        poller = _RecordingPoller()
        request = Request(
            {
                "type": "http",
                "app": SimpleNamespace(state=SimpleNamespace(poller=poller)),
            }
        )

        result = await read_usage(request, refresh=True)

        self.assertIs(result, poller.snapshot)
        self.assertEqual(poller.force_values, [True])


class CacheHeaderTests(unittest.TestCase):
    def test_live_api_responses_are_not_cacheable(self) -> None:
        settings = Settings(
            demo_mode=True,
            history_enabled=False,
            frontend_dist=Path("__missing_frontend_dist__"),
        )
        app = create_app(settings)

        with TestClient(app) as client:
            response = client.get("/api/usage")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")


def _old_codex_usage(captured_at: datetime) -> ProviderUsage:
    return ProviderUsage(
        id="codex",
        name="Codex",
        plan="Plus",
        windows=[
            UsageWindow(
                key="primary",
                label="7 Tage",
                used_percent=23,
                remaining_percent=77,
                resets_at=captured_at + timedelta(hours=1),
                window_minutes=10_080,
                primary=True,
            )
        ],
        source="logs",
        status="ok",
        fetched_at=captured_at,
    )


class LastKnownValueTests(unittest.TestCase):
    def test_bridge_keeps_an_old_value_after_its_reset(self) -> None:
        captured_at = datetime.now(timezone.utc) - timedelta(days=2)
        poller = UsagePoller(Settings(history_enabled=False))
        poller._last_good["codex"] = _old_codex_usage(captured_at)

        result = poller._bridge(
            build_error("codex", "Codex", "unauthorized", "Token abgelehnt")
        )

        self.assertTrue(result.stale)
        self.assertEqual(result.fetched_at, captured_at)
        self.assertEqual(result.windows[0].remaining_percent, 77)
        self.assertEqual(result.warning, "Token abgelehnt")

    def test_pruning_preserves_last_snapshot_for_restart(self) -> None:
        captured_at = datetime.now(timezone.utc) - timedelta(days=10)
        with TemporaryDirectory() as directory:
            store = SnapshotStore(Path(directory) / "usage.sqlite", retention_days=1)
            store.connect()
            try:
                store.record(captured_at, [_old_codex_usage(captured_at)])

                self.assertEqual(store.prune(), 0)
                restored = store.latest_per_provider()
            finally:
                store.close()

        self.assertEqual(len(restored), 1)
        self.assertTrue(restored[0].stale)
        self.assertEqual(restored[0].windows[0].remaining_percent, 77)


if __name__ == "__main__":
    unittest.main()
