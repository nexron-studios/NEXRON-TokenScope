from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.config import Settings
from app.providers.codex_api import CodexProvider, block_from_wham

# Gekürzte echte Antwort von `/backend-api/wham/usage` (September 2026),
# Kennungen entfernt. Die Fenster heißen hier `*_window` und messen in Sekunden.
WHAM_PAYLOAD = {
    "plan_type": "plus",
    "rate_limit": {
        "allowed": True,
        "limit_reached": False,
        "primary_window": {
            "used_percent": 15,
            "limit_window_seconds": 18000,
            "reset_after_seconds": 2539,
            "reset_at": 1789774341,
        },
        "secondary_window": {
            "used_percent": 87,
            "limit_window_seconds": 604800,
            "reset_after_seconds": 83980,
            "reset_at": 1789855782,
        },
    },
    "code_review_rate_limit": None,
    "credits": {"has_credits": False, "unlimited": False, "balance": "0"},
    "rate_limit_reached_type": None,
}


class BlockFromWhamTests(unittest.TestCase):
    def test_translates_windows_into_the_rollout_log_shape(self) -> None:
        block = block_from_wham(WHAM_PAYLOAD)

        assert block is not None
        self.assertEqual(block["plan_type"], "plus")
        self.assertEqual(block["primary"]["window_minutes"], 300)
        self.assertEqual(block["secondary"]["window_minutes"], 10080)
        self.assertEqual(block["primary"]["used_percent"], 15)

    def test_ignores_payloads_without_a_rate_limit_block(self) -> None:
        self.assertIsNone(block_from_wham({"rate_limits": {"primary": {}}}))
        self.assertIsNone(block_from_wham(["not", "a", "dict"]))

    def test_a_missing_secondary_window_is_skipped(self) -> None:
        payload = {
            "plan_type": "plus",
            "rate_limit": {
                "primary_window": WHAM_PAYLOAD["rate_limit"]["primary_window"],
                "secondary_window": None,
            },
        }

        block = block_from_wham(payload)

        assert block is not None
        self.assertIn("primary", block)
        self.assertNotIn("secondary", block)


class CodexProviderWhamTests(unittest.TestCase):
    def test_wham_payload_yields_both_windows(self) -> None:
        provider = CodexProvider(Settings(demo_mode=False))

        result = provider._from_payload(WHAM_PAYLOAD, source="api")

        assert result is not None
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.plan, "Plus")
        self.assertEqual([w.key for w in result.windows], ["primary", "secondary"])

        primary, secondary = result.windows
        self.assertTrue(primary.primary)
        self.assertEqual(primary.used_percent, 15.0)
        self.assertEqual(primary.label, "5 Stunden")
        self.assertEqual(
            primary.resets_at, datetime.fromtimestamp(1789774341, tz=timezone.utc)
        )
        self.assertEqual(secondary.used_percent, 87.0)
        self.assertEqual(secondary.label, "7 Tage")

    def test_rollout_log_shape_still_parses(self) -> None:
        provider = CodexProvider(Settings(demo_mode=False))
        block = {
            "primary": {"used_percent": 3, "window_minutes": 300},
            "secondary": {"used_percent": 78, "window_minutes": 10080},
            "_observed_at": "2026-09-17T16:44:02Z",
        }

        result = provider._from_payload({"rate_limits": block}, source="logs")

        assert result is not None
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.windows), 2)


if __name__ == "__main__":
    unittest.main()
