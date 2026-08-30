from __future__ import annotations

import asyncio
import unittest
from datetime import datetime, timedelta, timezone

from app.cli_refresh import CliRefresher, resolve_command
from app.config import Settings
from app.models import ProviderUsage, UsageWindow
from app.normalize import now
from app.poller import UsagePoller
from app.providers.base import build_error


class _StubRefresher:
    """Zählt Anstöße, ohne einen Prozess zu starten."""

    def __init__(self, *, allowed: bool = True) -> None:
        self.calls: list[str] = []
        self._allowed = allowed

    def may_attempt(self, provider_id: str) -> bool:
        return self._allowed

    async def trigger(self, provider_id: str) -> bool:
        self.calls.append(provider_id)
        # False beendet den Anstoß vor dem erneuten Abruf – der bräuchte einen
        # echten HTTP-Client.
        return False


def _bridged_claude() -> ProviderUsage:
    """Wie eine überbrückte Kachel aussieht: Werte da, Grund im warning_status."""
    captured_at = datetime.now(timezone.utc) - timedelta(hours=9)
    return ProviderUsage(
        id="claude",
        name="Claude Code",
        plan="Pro",
        windows=[
            UsageWindow(
                key="primary",
                label="5 Stunden",
                used_percent=12,
                remaining_percent=88,
                resets_at=captured_at + timedelta(hours=1),
                window_minutes=300,
                primary=True,
            )
        ],
        source="api",
        status="ok",
        fetched_at=captured_at,
        stale=True,
        warning="Token abgelaufen.",
        warning_status="auth_expired",
    )


async def _drain(poller: UsagePoller) -> None:
    await asyncio.gather(*list(poller._renewals))


class RenewalSchedulingTests(unittest.IsolatedAsyncioTestCase):
    def _poller(self, stub: _StubRefresher) -> UsagePoller:
        poller = UsagePoller(Settings(history_enabled=False))
        poller._refresher = stub  # type: ignore[assignment]
        return poller

    async def test_expired_token_triggers_the_cli_once(self) -> None:
        stub = _StubRefresher()
        poller = self._poller(stub)

        poller._schedule_renewals(
            [build_error("claude", "Claude Code", "auth_expired", "Token abgelaufen.")]
        )
        await _drain(poller)

        self.assertEqual(stub.calls, ["claude"])

    async def test_a_bridged_tile_still_triggers_the_cli(self) -> None:
        stub = _StubRefresher()
        poller = self._poller(stub)

        poller._schedule_renewals([_bridged_claude()])
        await _drain(poller)

        self.assertEqual(stub.calls, ["claude"])

    async def test_missing_login_is_left_alone(self) -> None:
        stub = _StubRefresher()
        poller = self._poller(stub)

        poller._schedule_renewals(
            [build_error("claude", "Claude Code", "auth_missing", "Nicht angemeldet.")]
        )
        await _drain(poller)

        self.assertEqual(stub.calls, [])

    async def test_a_blocked_refresher_is_not_asked_again(self) -> None:
        stub = _StubRefresher(allowed=False)
        poller = self._poller(stub)

        poller._schedule_renewals(
            [build_error("claude", "Claude Code", "auth_expired", "Token abgelaufen.")]
        )
        await _drain(poller)

        self.assertEqual(stub.calls, [])


class CliRefresherTests(unittest.TestCase):
    def test_cooldown_blocks_the_second_attempt(self) -> None:
        refresher = CliRefresher(
            Settings(history_enabled=False, cli_refresh_min_interval_seconds=300)
        )

        self.assertTrue(refresher.may_attempt("claude"))
        refresher._last_attempt_at["claude"] = now()

        self.assertFalse(refresher.may_attempt("claude"))

    def test_attempt_is_allowed_again_after_the_cooldown(self) -> None:
        refresher = CliRefresher(
            Settings(history_enabled=False, cli_refresh_min_interval_seconds=300)
        )
        refresher._last_attempt_at["claude"] = now() - timedelta(seconds=301)

        self.assertTrue(refresher.may_attempt("claude"))

    def test_provider_without_a_command_is_never_attempted(self) -> None:
        # Codex ist bewusst unbelegt, solange ungeklärt ist, ob die Konsole dort
        # überhaupt erneuert.
        refresher = CliRefresher(Settings(history_enabled=False))

        self.assertFalse(refresher.may_attempt("codex"))

    def test_unknown_command_resolves_to_nothing(self) -> None:
        self.assertIsNone(resolve_command(["__dieses_kommando_gibt_es_nicht__"]))

    def test_empty_command_resolves_to_nothing(self) -> None:
        self.assertIsNone(resolve_command([]))


if __name__ == "__main__":
    unittest.main()
