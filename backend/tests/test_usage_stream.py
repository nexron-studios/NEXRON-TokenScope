from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from starlette.requests import Request

from app.api import stream_usage
from app.config import Settings
from app.poller import UsagePoller


def _poller() -> UsagePoller:
    # Demo-Modus, damit kein Anbieter im Netz gefragt wird, und ein Intervall,
    # das waehrend des Tests garantiert nicht dazwischenfunkt.
    return UsagePoller(
        Settings(demo_mode=True, history_enabled=False, poll_interval_seconds=3600)
    )


class UsageStreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_snapshot_reaches_an_open_stream(self) -> None:
        poller = _poller()
        await poller.start()

        try:
            with poller.subscribe() as stream:
                self.assertTrue(stream.empty())

                await poller.refresh(force=True)

                self.assertIs(stream.get_nowait(), poller.snapshot)
        finally:
            await poller.stop()

    async def test_stream_keeps_only_the_newest_snapshot(self) -> None:
        poller = _poller()
        await poller.start()

        try:
            with poller.subscribe() as stream:
                await poller.refresh(force=True)
                await poller.refresh(force=True)

                self.assertIs(stream.get_nowait(), poller.snapshot)
                self.assertTrue(stream.empty())
        finally:
            await poller.stop()

    async def test_shutdown_ends_an_open_stream(self) -> None:
        poller = _poller()
        await poller.start()

        with poller.subscribe() as stream:
            await poller.stop()

            self.assertIsNone(stream.get_nowait())

    async def test_first_event_carries_the_current_snapshot(self) -> None:
        poller = _poller()
        await poller.start()
        request = Request(
            {
                "type": "http",
                "app": SimpleNamespace(state=SimpleNamespace(poller=poller)),
            }
        )

        try:
            response = await stream_usage(request)
            events = response.body_iterator
            first = await events.__anext__()
            await events.aclose()
        finally:
            await poller.stop()

        self.assertTrue(first.startswith("data: "))
        self.assertTrue(first.endswith("\n\n"))
        payload = json.loads(first[len("data: ") :])
        self.assertEqual(
            [item["id"] for item in payload["providers"]],
            [item.id for item in poller.snapshot.providers],
        )


if __name__ == "__main__":
    unittest.main()
