from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .models import HistoryPoint, HistorySeries, ProviderUsage, UsageWindow

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at   TEXT    NOT NULL,
    provider      TEXT    NOT NULL,
    window_key    TEXT    NOT NULL,
    label         TEXT    NOT NULL,
    used_percent  REAL    NOT NULL,
    resets_at     TEXT,
    source        TEXT    NOT NULL,
    UNIQUE(captured_at, provider, window_key)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_series
    ON snapshots(provider, window_key, captured_at);
"""

# Nachträglich ergänzte Spalten. `CREATE TABLE IF NOT EXISTS` fasst eine
# bestehende Tabelle nicht an, deshalb hier einzeln nachziehen.
_ADDED_COLUMNS = {
    "plan": "TEXT",
    "window_minutes": "INTEGER",
    "is_primary": "INTEGER NOT NULL DEFAULT 0",
}


class SnapshotStore:
    """Schreibt jeden Poll als Snapshot nach SQLite.

    Bewusst ohne ORM: eine Tabelle, zwei Abfragen, keine Migrationskette.
    Der Store lebt rein lokal und enthält keinerlei Tokenmaterial.
    """

    def __init__(self, database_path: Path, retention_days: int = 90) -> None:
        self._path = database_path
        self._retention_days = retention_days
        self._connection: sqlite3.Connection | None = None

    def connect(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self._path, check_same_thread=False, isolation_level=None
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.executescript(_SCHEMA)
        self._migrate(connection)
        self._connection = connection

    @staticmethod
    def _migrate(connection: sqlite3.Connection) -> None:
        existing = {
            row["name"] for row in connection.execute("PRAGMA table_info(snapshots)")
        }
        for column, definition in _ADDED_COLUMNS.items():
            if column not in existing:
                connection.execute(
                    f"ALTER TABLE snapshots ADD COLUMN {column} {definition}"
                )
                logger.info("Snapshot-Tabelle um Spalte %s ergänzt", column)

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    @property
    def is_open(self) -> bool:
        return self._connection is not None

    def record(self, captured_at: datetime, providers: Iterable[ProviderUsage]) -> int:
        if self._connection is None:
            return 0

        stamp = captured_at.astimezone(timezone.utc).isoformat()
        rows = [
            (
                stamp,
                provider.id,
                window.key,
                window.label,
                window.used_percent,
                window.resets_at.astimezone(timezone.utc).isoformat()
                if window.resets_at
                else None,
                provider.source,
                provider.plan,
                window.window_minutes,
                1 if window.primary else 0,
            )
            for provider in providers
            # Überbrückte Werte sind eine Wiederholung des letzten Abrufs –
            # als frischer Messpunkt gespeichert würden sie den Verlauf
            # zu einer erfundenen Geraden glätten.
            if provider.status == "ok" and not provider.stale
            for window in provider.windows
        ]
        if not rows:
            return 0

        try:
            self._connection.executemany(
                """
                INSERT OR REPLACE INTO snapshots
                    (captured_at, provider, window_key, label, used_percent,
                     resets_at, source, plan, window_minutes, is_primary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        except sqlite3.Error as exc:
            logger.warning("Snapshot konnte nicht gespeichert werden: %s", exc)
            return 0
        return len(rows)

    def history(self, *, hours: int, provider: str | None = None) -> list[HistorySeries]:
        if self._connection is None:
            return []

        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = """
            SELECT provider, window_key, label, captured_at, used_percent
            FROM snapshots
            WHERE captured_at >= ?
        """
        params: list[object] = [since.isoformat()]
        if provider:
            query += " AND provider = ?"
            params.append(provider)
        query += " ORDER BY provider, window_key, captured_at"

        try:
            rows = self._connection.execute(query, params).fetchall()
        except sqlite3.Error as exc:
            logger.warning("Historie konnte nicht gelesen werden: %s", exc)
            return []

        series: dict[tuple[str, str], HistorySeries] = {}
        for row in rows:
            key = (row["provider"], row["window_key"])
            entry = series.get(key)
            if entry is None:
                entry = HistorySeries(
                    provider=row["provider"],
                    window_key=row["window_key"],
                    label=row["label"],
                    points=[],
                )
                series[key] = entry
            entry.points.append(
                HistoryPoint(
                    captured_at=datetime.fromisoformat(row["captured_at"]),
                    used_percent=row["used_percent"],
                )
            )

        return list(series.values())

    def latest_per_provider(self) -> list[ProviderUsage]:
        """Rekonstruiert den zuletzt gespeicherten Stand je Anbieter.

        Damit steht nach einem Neustart sofort wieder ein Überbrückungswert
        bereit, statt dass die Kachel leer bleibt, bis der erste Poll glückt.
        Die Werte sind als ``stale`` markiert und werden als historischer Stand
        angezeigt, wenn der frische Abruf weiterhin scheitert.
        """
        if self._connection is None:
            return []

        try:
            rows = self._connection.execute(
                """
                SELECT s.provider, s.window_key, s.label, s.used_percent,
                       s.resets_at, s.source, s.plan, s.window_minutes,
                       s.is_primary, s.captured_at
                FROM snapshots AS s
                JOIN (
                    SELECT provider, MAX(captured_at) AS captured_at
                    FROM snapshots
                    GROUP BY provider
                ) AS newest
                  ON newest.provider = s.provider
                 AND newest.captured_at = s.captured_at
                """
            ).fetchall()
        except sqlite3.Error as exc:
            logger.warning("Letzter Stand nicht lesbar: %s", exc)
            return []

        grouped: dict[str, list[sqlite3.Row]] = {}
        for row in rows:
            grouped.setdefault(row["provider"], []).append(row)

        restored: list[ProviderUsage] = []
        for provider_id, entries in grouped.items():
            newest = max(entries, key=lambda row: row["captured_at"])
            windows = [
                UsageWindow(
                    key=row["window_key"],
                    label=row["label"],
                    used_percent=row["used_percent"],
                    remaining_percent=max(0.0, 100.0 - row["used_percent"]),
                    resets_at=datetime.fromisoformat(row["resets_at"])
                    if row["resets_at"]
                    else None,
                    window_minutes=row["window_minutes"],
                    primary=bool(row["is_primary"]),
                )
                for row in entries
            ]
            windows.sort(key=lambda item: (item.window_minutes or 10**9, item.key))

            restored.append(
                ProviderUsage(
                    id=provider_id,  # type: ignore[arg-type]
                    name="Claude Code" if provider_id == "claude" else "Codex",
                    plan=newest["plan"],
                    windows=windows,
                    source=newest["source"],
                    status="ok",
                    stale=True,
                    fetched_at=datetime.fromisoformat(newest["captured_at"]),
                )
            )

        return restored

    def prune(self) -> int:
        if self._connection is None or self._retention_days <= 0:
            return 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        try:
            cursor = self._connection.execute(
                """
                DELETE FROM snapshots
                WHERE captured_at < ?
                  AND captured_at <> (
                      SELECT MAX(latest.captured_at)
                      FROM snapshots AS latest
                      WHERE latest.provider = snapshots.provider
                  )
                """,
                (cutoff.isoformat(),),
            )
        except sqlite3.Error as exc:
            logger.warning("Aufräumen fehlgeschlagen: %s", exc)
            return 0
        return cursor.rowcount or 0
