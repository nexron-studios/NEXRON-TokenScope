from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Iterable, Literal

from ..config import Settings
from ..models import ActivityCell, LogBucket, LogInsights, LogSummary, TokenTotals
from ..normalize import now
from .claude_jsonl import read_claude_records
from .codex_jsonl import read_codex_records
from .records import LogRecord

GroupBy = Literal["day", "project", "model", "provider"]


def _add(target: TokenTotals, value: TokenTotals) -> None:
    target.input_tokens += value.input_tokens
    target.output_tokens += value.output_tokens
    target.cache_write_tokens += value.cache_write_tokens
    target.cache_read_tokens += value.cache_read_tokens


def _group_value(record: LogRecord, group_by: GroupBy) -> tuple[str, str]:
    if group_by == "day":
        local = record.observed_at.astimezone()
        return local.date().isoformat(), local.strftime("%d.%m.%Y")
    if group_by == "project":
        return record.project.casefold(), record.project
    if group_by == "model":
        return record.model.casefold(), record.model
    label = "Claude" if record.provider == "claude" else "Codex"
    return record.provider, label


def _streaks(active: set[date], today: date) -> tuple[int, int]:
    """Aktuelle und längste Serie aufeinanderfolgender aktiver Tage."""
    if not active:
        return 0, 0

    ordered = sorted(active)
    longest = run = 1
    for previous, current in zip(ordered, ordered[1:]):
        run = run + 1 if (current - previous).days == 1 else 1
        longest = max(longest, run)

    # Der heutige Tag darf noch leer sein, ohne die laufende Serie zu brechen –
    # sonst stünde jeden Morgen bis zur ersten Nachricht eine Null da.
    cursor = today if today in active else today - timedelta(days=1)
    streak = 0
    while cursor in active:
        streak += 1
        cursor -= timedelta(days=1)
    return streak, longest


def _insights(records: Iterable[LogRecord]) -> LogInsights:
    sessions: set[tuple[str, str]] = set()
    active_days: set[date] = set()
    hours: Counter[int] = Counter()
    models: Counter[str] = Counter()
    grid: dict[tuple[int, int], list[int]] = {}
    messages = 0

    for record in records:
        messages += 1
        sessions.add((record.provider, record.session))
        # Alles Zeitliche in Ortszeit: „23 Uhr“ meint die Uhr an der Wand,
        # nicht UTC.
        local = record.observed_at.astimezone()
        active_days.add(local.date())
        hours[local.hour] += 1
        models[record.model] += 1
        cell = grid.setdefault((local.weekday(), local.hour), [0, 0])
        cell[0] += 1
        cell[1] += record.totals.total

    current_streak, longest_streak = _streaks(active_days, now().astimezone().date())
    top_model, top_model_messages = (
        models.most_common(1)[0] if models else (None, 0)
    )

    return LogInsights(
        sessions=len(sessions),
        messages=messages,
        active_days=len(active_days),
        current_streak=current_streak,
        longest_streak=longest_streak,
        peak_hour=hours.most_common(1)[0][0] if hours else None,
        top_model=top_model,
        top_model_messages=top_model_messages,
        activity=[
            ActivityCell(
                weekday=weekday, hour=hour, messages=count, tokens=tokens
            )
            for (weekday, hour), (count, tokens) in sorted(grid.items())
        ],
    )


class LogStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def summary(self, *, days: int, group_by: GroupBy) -> LogSummary:
        since = now() - timedelta(days=days)
        claude = read_claude_records(self._settings.claude_projects_dir, since)
        codex = read_codex_records(self._settings.codex_sessions_dir, since)
        records = [*claude.records, *codex.records]

        totals = TokenTotals()
        grouped: dict[tuple[str, str], tuple[str, int, TokenTotals]] = {}
        for record in records:
            _add(totals, record.totals)
            raw_key, label = _group_value(record, group_by)
            key = (record.provider, raw_key)
            current_label, messages, bucket_totals = grouped.get(
                key, (label, 0, TokenTotals())
            )
            _add(bucket_totals, record.totals)
            grouped[key] = (current_label, messages + 1, bucket_totals)

        buckets = [
            LogBucket(
                key=f"{provider}:{raw_key}",
                label=label,
                provider=provider,
                messages=messages,
                totals=bucket_totals,
            )
            for (provider, raw_key), (label, messages, bucket_totals) in grouped.items()
        ]
        buckets.sort(key=lambda bucket: bucket.totals.total, reverse=True)

        return LogSummary(
            since=since,
            days=days,
            group_by=group_by,
            scanned_files=claude.scanned_files + codex.scanned_files,
            skipped_lines=claude.skipped_lines + codex.skipped_lines,
            totals=totals,
            buckets=buckets,
            insights=_insights(records),
        )
