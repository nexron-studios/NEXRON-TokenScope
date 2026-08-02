from __future__ import annotations

from datetime import timedelta
from typing import Literal

from ..config import Settings
from ..models import LogBucket, LogSummary, TokenTotals
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
        )
