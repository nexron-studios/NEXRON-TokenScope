from __future__ import annotations

import json
import sqlite3
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from app.claude_accounts import ClaudeAccount, discover_claude_accounts
from app.config import Settings
from app.logs import LogStore
from app.models import AccountInfo, ProviderUsage, UsageWindow
from app.providers.claude_api import ClaudeProvider
from app.storage import SnapshotStore

PRIVATE = "uuid-private"
WORK = "uuid-work"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _login(directory: Path, *, expires_in_hours: float, token: str) -> None:
    expires = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
    _write_json(
        directory / ".credentials.json",
        {
            "claudeAiOauth": {
                "accessToken": token,
                "expiresAt": int(expires.timestamp() * 1000),
                "subscriptionType": "max",
            }
        },
    )


def _identity(path: Path, uuid: str, email: str) -> None:
    _write_json(path, {"oauthAccount": {"accountUuid": uuid, "emailAddress": email}})


def _home_with_three_dirs(home: Path) -> None:
    """~/.claude und ~/.claude-gmail am selben Account, ~/.claude-mackone separat."""
    _login(home / ".claude", expires_in_hours=1, token="a")
    _identity(home / ".claude.json", PRIVATE, "jonas@example.com")
    _login(home / ".claude-gmail", expires_in_hours=1, token="b")
    _identity(home / ".claude-gmail" / ".claude.json", PRIVATE, "jonas@example.com")
    _login(home / ".claude-mackone", expires_in_hours=1, token="c")
    _identity(home / ".claude-mackone" / ".claude.json", WORK, "jonas@work.example")
    # Ein fremdes Tool mit ähnlichem Namen, ohne Login.
    (home / ".claude-server-commander").mkdir()


def _usage(account: str, used: float) -> ProviderUsage:
    return ProviderUsage(
        id="claude",
        name="Claude Code",
        account=AccountInfo(id=account, name=account),
        windows=[
            UsageWindow(
                key="five_hour",
                label="5 Stunden",
                used_percent=used,
                remaining_percent=100 - used,
                window_minutes=300,
                primary=True,
            )
        ],
        source="api",
        status="ok",
        fetched_at=datetime.now(timezone.utc),
    )


class DiscoveryTests(unittest.TestCase):
    def test_dirs_of_the_same_account_become_one_entry(self) -> None:
        with TemporaryDirectory() as directory:
            home = Path(directory)
            _home_with_three_dirs(home)

            accounts = discover_claude_accounts(Settings(), home)

        self.assertEqual(
            [(a.info.id, a.info.name, len(a.config_dirs)) for a in accounts],
            [(PRIVATE, "gmail", 2), (WORK, "mackone", 1)],
        )
        self.assertEqual(accounts[1].info.email, "jonas@work.example")

    def test_a_single_default_login_is_named_after_the_mail(self) -> None:
        with TemporaryDirectory() as directory:
            home = Path(directory)
            _login(home / ".claude", expires_in_hours=1, token="a")
            _identity(home / ".claude.json", PRIVATE, "jonas@example.com")

            accounts = discover_claude_accounts(Settings(), home)

        self.assertEqual([a.info.name for a in accounts], ["jonas"])


class CredentialChoiceTests(unittest.TestCase):
    def test_a_fresh_token_in_the_second_dir_wins_over_an_expired_first(self) -> None:
        with TemporaryDirectory() as directory:
            home = Path(directory)
            _login(home / ".claude", expires_in_hours=-1, token="expired")
            _login(home / ".claude-gmail", expires_in_hours=1, token="fresh")
            account = ClaudeAccount(
                info=AccountInfo(id=PRIVATE, name="gmail"),
                config_dirs=(home / ".claude", home / ".claude-gmail"),
            )
            provider = ClaudeProvider(Settings(), account, home)

            credential = provider._load_credential()

            self.assertEqual(credential.access_token, "fresh")
            self.assertEqual(
                provider.refresh_env,
                {"CLAUDE_CONFIG_DIR": str(home / ".claude-gmail")},
            )


class StorageTests(unittest.TestCase):
    def test_two_accounts_polled_at_once_keep_both_rows(self) -> None:
        moment = datetime.now(timezone.utc)
        with TemporaryDirectory() as directory:
            store = SnapshotStore(Path(directory) / "usage.sqlite")
            store.connect()
            try:
                store.record(moment, [_usage(PRIVATE, 10), _usage(WORK, 70)])
                series = store.history(hours=1)
            finally:
                store.close()

        self.assertEqual(
            sorted((entry.account, entry.points[0].used_percent) for entry in series),
            [(PRIVATE, 10), (WORK, 70)],
        )

    def test_rows_from_before_accounts_go_to_the_default_login(self) -> None:
        stamp = datetime.now(timezone.utc).isoformat()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "usage.sqlite"
            legacy = sqlite3.connect(path)
            legacy.executescript(
                """
                CREATE TABLE snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    captured_at TEXT NOT NULL, provider TEXT NOT NULL,
                    window_key TEXT NOT NULL, label TEXT NOT NULL,
                    used_percent REAL NOT NULL, resets_at TEXT,
                    source TEXT NOT NULL,
                    UNIQUE(captured_at, provider, window_key)
                );
                """
            )
            legacy.executemany(
                "INSERT INTO snapshots (captured_at, provider, window_key, label,"
                " used_percent, source) VALUES (?, ?, 'five_hour', '5 Stunden', ?, 'api')",
                [(stamp, "claude", 42), (stamp, "codex", 7)],
            )
            legacy.commit()
            legacy.close()

            store = SnapshotStore(path)
            store.connect()
            try:
                adopted = store.adopt_legacy("claude", PRIVATE)
                series = store.history(hours=1)
            finally:
                store.close()

        self.assertEqual(adopted, 1)
        self.assertEqual(
            sorted((entry.provider, entry.account) for entry in series),
            [("claude", PRIVATE), ("codex", "")],
        )


class LogExcludeTests(unittest.TestCase):
    def test_a_hidden_login_drops_out_of_the_summary(self) -> None:
        stamp = datetime.now(timezone.utc).isoformat()
        with TemporaryDirectory() as directory:
            home = Path(directory)
            accounts = []
            for uuid, folder, count in ((PRIVATE, ".claude", 2), (WORK, ".claude-mackone", 5)):
                lines = [
                    json.dumps(
                        {
                            "type": "assistant",
                            "timestamp": stamp,
                            "sessionId": f"{uuid}-session",
                            "message": {
                                "id": f"{uuid}-{index}",
                                "model": "claude-opus",
                                "usage": {"input_tokens": 10, "output_tokens": 1},
                            },
                        }
                    )
                    for index in range(count)
                ]
                log = home / folder / "projects" / "demo" / "session.jsonl"
                log.parent.mkdir(parents=True)
                log.write_text("\n".join(lines), encoding="utf-8")
                accounts.append(
                    ClaudeAccount(
                        info=AccountInfo(id=uuid, name=folder),
                        config_dirs=(home / folder,),
                    )
                )
            store = LogStore(Settings(codex_sessions_dir=home / "none"), accounts)

            both = store.summary(days=1, group_by="day")
            private_only = store.summary(
                days=1, group_by="day", exclude=frozenset({f"claude:{WORK}"})
            )

        self.assertEqual(both.insights.messages, 7)
        self.assertEqual(private_only.insights.messages, 2)


if __name__ == "__main__":
    unittest.main()
