from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import TokenTotals
from ..normalize import parse_timestamp
from .records import LogRecord, ReadResult, project_name, token_count


def read_codex_records(root: Path, since: datetime) -> ReadResult:
    result = ReadResult()
    if not root.is_dir():
        return result

    for path in root.rglob("*.jsonl"):
        try:
            if path.stat().st_mtime < since.timestamp():
                continue
            handle = path.open("r", encoding="utf-8", errors="replace")
        except OSError:
            result.skipped_lines += 1
            continue

        result.scanned_files += 1
        cwd: object = None
        model: object = None

        with handle:
            for line in handle:
                try:
                    item = json.loads(line)
                except (json.JSONDecodeError, UnicodeError):
                    result.skipped_lines += 1
                    continue
                if not isinstance(item, dict):
                    continue

                payload = item.get("payload")
                if not isinstance(payload, dict):
                    continue

                if item.get("type") == "session_meta":
                    cwd = payload.get("cwd") or cwd
                    continue
                if item.get("type") == "turn_context":
                    cwd = payload.get("cwd") or cwd
                    model = payload.get("model") or model
                    continue
                if item.get("type") != "event_msg" or payload.get("type") != "token_count":
                    continue

                info = payload.get("info")
                usage = info.get("last_token_usage") if isinstance(info, dict) else None
                if not isinstance(usage, dict):
                    continue

                observed_at = parse_timestamp(item.get("timestamp"))
                if observed_at is None or observed_at < since:
                    continue

                result.records.append(
                    LogRecord(
                        observed_at=observed_at,
                        provider="codex",
                        project=project_name(cwd, path.parent.name),
                        model=model if isinstance(model, str) and model else "Unbekannt",
                        totals=TokenTotals(
                            input_tokens=token_count(usage.get("input_tokens")),
                            output_tokens=token_count(usage.get("output_tokens")),
                            cache_write_tokens=token_count(
                                usage.get("cache_write_input_tokens")
                            ),
                            cache_read_tokens=token_count(
                                usage.get("cached_input_tokens")
                            ),
                        ),
                    )
                )

    return result


def latest_codex_rate_limits(root: Path) -> dict[str, Any] | None:
    """Liest den zeitlich neuesten Rate-Limit-Block aus den Rollout-Logs."""
    latest_at: datetime | None = None
    latest: dict[str, Any] | None = None
    if not root.is_dir():
        return None

    for path in root.rglob("*.jsonl"):
        try:
            handle = path.open("r", encoding="utf-8", errors="replace")
        except OSError:
            continue

        with handle:
            for line in handle:
                try:
                    item = json.loads(line)
                except (json.JSONDecodeError, UnicodeError):
                    continue
                if not isinstance(item, dict):
                    continue
                payload = item.get("payload")
                if not isinstance(payload, dict):
                    continue
                block = payload.get("rate_limits")
                if not isinstance(block, dict):
                    continue

                observed_at = parse_timestamp(item.get("timestamp"))
                if observed_at is None or (latest_at is not None and observed_at <= latest_at):
                    continue
                latest_at = observed_at
                latest = dict(block)

    if latest is not None and latest_at is not None:
        latest["_observed_at"] = latest_at.isoformat()
    return latest
