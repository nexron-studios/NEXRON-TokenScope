from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..models import TokenTotals
from ..normalize import parse_timestamp
from .records import LogRecord, ReadResult, project_name, token_count


def read_claude_records(root: Path, since: datetime) -> ReadResult:
    result = ReadResult()
    if not root.is_dir():
        return result

    # Claude schreibt bei Tool-Nutzung dieselbe Assistant-Nachricht mehrfach
    # mit identischer Usage. Die Message-ID verhindert Doppelzaehlung.
    messages: dict[str, LogRecord] = {}

    for path in root.rglob("*.jsonl"):
        try:
            if path.stat().st_mtime < since.timestamp():
                continue
            handle = path.open("r", encoding="utf-8", errors="replace")
        except OSError:
            result.skipped_lines += 1
            continue

        result.scanned_files += 1
        with handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    item = json.loads(line)
                except (json.JSONDecodeError, UnicodeError):
                    result.skipped_lines += 1
                    continue

                if not isinstance(item, dict) or item.get("type") != "assistant":
                    continue
                message = item.get("message")
                if not isinstance(message, dict):
                    continue
                usage = message.get("usage")
                if not isinstance(usage, dict):
                    continue

                observed_at = parse_timestamp(item.get("timestamp"))
                if observed_at is None or observed_at < since:
                    continue

                identity = (
                    message.get("id")
                    or item.get("requestId")
                    or item.get("uuid")
                    or f"{path}:{line_number}"
                )
                model = message.get("model")
                messages[str(identity)] = LogRecord(
                    observed_at=observed_at,
                    provider="claude",
                    project=project_name(item.get("cwd"), path.parent.name),
                    model=model if isinstance(model, str) and model else "Unbekannt",
                    totals=TokenTotals(
                        input_tokens=token_count(usage.get("input_tokens")),
                        output_tokens=token_count(usage.get("output_tokens")),
                        cache_write_tokens=token_count(
                            usage.get("cache_creation_input_tokens")
                        ),
                        cache_read_tokens=token_count(
                            usage.get("cache_read_input_tokens")
                        ),
                    ),
                )

    result.records.extend(messages.values())
    return result
