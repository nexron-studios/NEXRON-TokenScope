from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from app.service_status import CLAUDE, CODEX, ServiceStatusError, build_status

AT = datetime(2026, 9, 29, 15, 0, tzinfo=timezone.utc)


def component(name: str, status: str = "operational") -> dict:
    return {"name": name, "status": status}


COMPONENTS = [
    component("claude.ai"),
    component("Claude Console (platform.claude.com)"),
    component("Claude API (api.anthropic.com)"),
    component("Claude Code"),
    component("Claude Cowork"),
]

# Gekürzt nach der echten Meldung vom 29.09.2026.
OUTAGE = {
    "name": "Elevated errors on claude.ai, Claude Code, Claude Cowork and the Claude API",
    "status": "identified",
    "impact": "major",
    "created_at": "2026-09-29T14:21:37.188Z",
    "resolved_at": None,
    "shortlink": "https://stspg.io/br61xzj05pp5",
    "components": [{"name": "Claude Code"}, {"name": "Claude API (api.anthropic.com)"}],
}


def summary(**overrides: object) -> dict:
    return {"components": COMPONENTS, "incidents": [], "scheduled_maintenances": [], **overrides}


class ClaudeStatusTests(unittest.TestCase):
    def test_all_operational_is_ok(self) -> None:
        status = build_status(summary(), {"incidents": []}, source=CLAUDE, at=AT)

        self.assertEqual(status.level, "ok")
        self.assertEqual(status.incidents, [])

    def test_only_components_that_matter_here_are_kept(self) -> None:
        status = build_status(summary(), {"incidents": []}, source=CLAUDE, at=AT)

        self.assertEqual(
            [c.name for c in status.components], ["claude.ai", "Claude API", "Claude Code"]
        )

    def test_an_open_major_incident_is_an_outage(self) -> None:
        status = build_status(summary(incidents=[OUTAGE]), {"incidents": []}, source=CLAUDE, at=AT)

        self.assertEqual(status.level, "outage")
        self.assertEqual(status.incidents[0].url, "https://stspg.io/br61xzj05pp5")

    def test_a_broken_component_raises_the_level_without_an_incident(self) -> None:
        components = [*COMPONENTS[:3], component("Claude Code", "degraded_performance")]

        status = build_status(summary(components=components), {"incidents": []}, source=CLAUDE, at=AT)

        self.assertEqual(status.level, "degraded")

    def test_an_incident_on_cowork_alone_is_ignored(self) -> None:
        cowork = {**OUTAGE, "components": [{"name": "Claude Cowork"}]}

        status = build_status(summary(incidents=[cowork]), {"incidents": []}, source=CLAUDE, at=AT)

        self.assertEqual(status.level, "ok")
        self.assertEqual(status.incidents, [])

    def test_an_incident_without_components_still_counts(self) -> None:
        untagged = {**OUTAGE, "impact": "minor", "components": []}

        status = build_status(summary(incidents=[untagged]), {"incidents": []}, source=CLAUDE, at=AT)

        self.assertEqual(status.level, "degraded")

    def test_a_fresh_resolution_is_reported(self) -> None:
        resolved = {**OUTAGE, "status": "resolved", "resolved_at": "2026-09-29T14:40:00Z"}

        status = build_status(summary(), {"incidents": [resolved]}, source=CLAUDE, at=AT)

        self.assertIsNotNone(status.recently_resolved)
        self.assertEqual(status.level, "ok")

    def test_an_old_resolution_is_not_reported(self) -> None:
        resolved = {**OUTAGE, "status": "resolved", "resolved_at": "2026-09-28T10:00:00Z"}

        status = build_status(summary(), {"incidents": [resolved]}, source=CLAUDE, at=AT)

        self.assertIsNone(status.recently_resolved)

    def test_maintenance_within_the_lookahead_is_announced(self) -> None:
        upcoming = {
            "name": "Database maintenance",
            "status": "scheduled",
            "scheduled_for": (AT + timedelta(hours=2)).isoformat(),
        }

        status = build_status(summary(scheduled_maintenances=[upcoming]), {}, source=CLAUDE, at=AT)

        self.assertIsNotNone(status.maintenance)
        self.assertEqual(status.level, "ok")

    def test_maintenance_far_ahead_is_not_announced(self) -> None:
        later = {
            "name": "Database maintenance",
            "status": "scheduled",
            "scheduled_for": (AT + timedelta(days=2)).isoformat(),
        }

        status = build_status(summary(scheduled_maintenances=[later]), {}, source=CLAUDE, at=AT)

        self.assertIsNone(status.maintenance)

    def test_an_unexpected_shape_is_rejected(self) -> None:
        with self.assertRaises(ServiceStatusError):
            build_status(["not", "a", "dict"], {}, source=CLAUDE, at=AT)


# Gekürzt nach status.openai.com vom 30.09.2026: incident.io liefert Störungen
# ohne Komponenten und ohne Kurzlink.
OPENAI_COMPONENTS = [
    component("Conversations", "degraded_performance"),
    component("CLI"),
    component("Login"),
    component("Responses"),
]


def openai_incident(name: str, **overrides: object) -> dict:
    return {
        "id": "01M3RDNY37CAPQGRKPBVMNRT4K",
        "name": name,
        "status": "monitoring",
        "impact": "minor",
        "created_at": "2026-09-30T05:47:57Z",
        **overrides,
    }


def openai_summary(**overrides: object) -> dict:
    return {"components": OPENAI_COMPONENTS, "incidents": [], **overrides}


class CodexStatusTests(unittest.TestCase):
    def test_a_chatgpt_only_incident_is_ignored(self) -> None:
        chatgpt = openai_incident("Elevated error rates for ChatGPT Pro and Plus users")

        status = build_status(openai_summary(incidents=[chatgpt]), {}, source=CODEX, at=AT)

        self.assertEqual(status.level, "ok")
        self.assertEqual(status.incidents, [])

    def test_a_degraded_chatgpt_component_is_ignored(self) -> None:
        status = build_status(openai_summary(), {}, source=CODEX, at=AT)

        self.assertEqual([c.name for c in status.components], ["CLI", "Login"])
        self.assertEqual(status.level, "ok")

    def test_an_incident_naming_codex_counts(self) -> None:
        codex = openai_incident("Issues with Codex ", impact="critical")

        status = build_status(openai_summary(incidents=[codex]), {}, source=CODEX, at=AT)

        self.assertEqual(status.level, "outage")
        self.assertEqual(status.incidents[0].name, "Issues with Codex")

    def test_an_incident_without_shortlink_links_to_its_page(self) -> None:
        codex = openai_incident("Elevated errors across ChatGPT, Codex, and the API")

        status = build_status(openai_summary(incidents=[codex]), {}, source=CODEX, at=AT)

        self.assertEqual(
            status.incidents[0].url,
            "https://status.openai.com/incidents/01M3RDNY37CAPQGRKPBVMNRT4K",
        )

    def test_a_broken_cli_component_counts(self) -> None:
        components = [component("CLI", "partial_outage"), component("Login")]

        status = build_status({"components": components}, {}, source=CODEX, at=AT)

        self.assertEqual(status.level, "outage")
        self.assertEqual(status.provider, "codex")


if __name__ == "__main__":
    unittest.main()
