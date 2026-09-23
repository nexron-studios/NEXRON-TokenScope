from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.weather import WeatherError, build_report

# Gekürzte echte Antwort von api.open-meteo.com mit `timezone=auto`:
# `current.time` ist Ortszeit ohne Zeitzone, der Versatz steht daneben.
FORECAST = {
    "utc_offset_seconds": 7200,
    "timezone": "Europe/Berlin",
    "current": {
        "time": "2026-09-23T14:45",
        "temperature_2m": 21.5,
        "apparent_temperature": 20.1,
        "is_day": 1,
        "weather_code": 0,
    },
    "daily": {
        "time": ["2026-09-23"],
        "temperature_2m_max": [22.3],
        "temperature_2m_min": [7.4],
    },
}


class BuildReportTests(unittest.TestCase):
    def test_reads_current_and_daily_values(self) -> None:
        report = build_report(FORECAST, place="Lahr")

        self.assertEqual(report.place, "Lahr")
        self.assertEqual(report.temperature, 21.5)
        self.assertEqual(report.feels_like, 20.1)
        self.assertEqual(report.day_high, 22.3)
        self.assertEqual(report.day_low, 7.4)
        self.assertTrue(report.is_day)

    def test_local_time_is_converted_to_utc(self) -> None:
        report = build_report(FORECAST, place="Lahr")

        # 14:45 Ortszeit bei +2 h sind 12:45 UTC. Ungerechnet läge der
        # Messzeitpunkt zwei Stunden in der Zukunft.
        self.assertEqual(
            report.observed_at, datetime(2026, 9, 23, 12, 45, tzinfo=timezone.utc)
        )

    def test_a_missing_daily_block_is_not_fatal(self) -> None:
        payload = {k: v for k, v in FORECAST.items() if k != "daily"}

        report = build_report(payload, place="")

        self.assertIsNone(report.day_high)
        self.assertIsNone(report.day_low)
        self.assertEqual(report.temperature, 21.5)

    def test_an_answer_without_a_temperature_is_rejected(self) -> None:
        with self.assertRaises(WeatherError):
            build_report({"current": {"time": "2026-09-23T14:45"}}, place="Lahr")

    def test_an_unexpected_shape_is_rejected(self) -> None:
        with self.assertRaises(WeatherError):
            build_report(["not", "a", "dict"], place="Lahr")


if __name__ == "__main__":
    unittest.main()
