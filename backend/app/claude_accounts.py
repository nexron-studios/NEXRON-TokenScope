"""Findet die Claude-Code-Logins auf diesem Rechner.

Wer mit mehreren Accounts arbeitet, startet Claude Code mit je eigenem
``CLAUDE_CONFIG_DIR`` (etwa ``~/.claude-mackone``). Jeder dieser Ordner hat
eigene Credentials und eigene Sitzungslogs und damit ein eigenes Kontingent.
Zwei Ordner können aber am selben Account hängen; die teilen sich das
Kontingent und werden deshalb zu einer Kachel zusammengefasst.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from .config import Settings
from .models import AccountInfo

logger = logging.getLogger(__name__)

DEFAULT_DIR_NAME = ".claude"
DIR_PREFIX = ".claude-"
CREDENTIALS_FILE = ".credentials.json"
GLOBAL_CONFIG_FILE = ".claude.json"
#: Die CLI schreibt `.claude.json` laufend neu. Ein halb geschriebener Stand
#: darf den Account nicht unter einer Ersatz-ID landen lassen – sonst zerfällt
#: sein Verlauf in zwei Serien.
IDENTITY_READ_ATTEMPTS = 3
IDENTITY_RETRY_SECONDS = 0.05


@dataclass(frozen=True)
class ClaudeAccount:
    info: AccountInfo
    #: Vorrangreihenfolge – ``~/.claude`` zuerst, wenn es dazugehört.
    config_dirs: tuple[Path, ...]

    @property
    def credential_paths(self) -> list[Path]:
        return [directory / CREDENTIALS_FILE for directory in self.config_dirs]

    @property
    def projects_dirs(self) -> list[Path]:
        return [directory / "projects" for directory in self.config_dirs]


def is_default_dir(directory: Path, home: Path) -> bool:
    return directory == home / DEFAULT_DIR_NAME


def _has_login(directory: Path) -> bool:
    # `.claude.json` allein genügt: Auf macOS liegt der Token im Keychain.
    return (directory / CREDENTIALS_FILE).is_file() or (
        directory / GLOBAL_CONFIG_FILE
    ).is_file()


def candidate_dirs(configured: list[Path], home: Path) -> list[Path]:
    if configured:
        return [path.expanduser() for path in configured]
    default = home / DEFAULT_DIR_NAME
    extra = sorted(
        path for path in home.glob(f"{DIR_PREFIX}*") if path.is_dir() and _has_login(path)
    )
    # Ohne jeden Login bleibt `~/.claude` stehen, damit die Kachel sagt, was fehlt.
    if extra and not (default / CREDENTIALS_FILE).is_file() and not (
        home / GLOBAL_CONFIG_FILE
    ).is_file():
        return extra
    return [default, *extra]


def keychain_service_for(directory: Path, home: Path, base: str) -> str:
    """Name des Keychain-Eintrags, unter dem die CLI den Token dieses Ordners ablegt."""
    if is_default_dir(directory, home):
        return base
    # shortcut: Suffix nach dem Schema der CLI (sha256 des Pfads, 8 Zeichen),
    # auf macOS noch nicht nachgemessen. Passt es nicht, greift die Datei.
    return f"{base}-{hashlib.sha256(str(directory).encode()).hexdigest()[:8]}"


def _global_config_path(directory: Path, home: Path) -> Path:
    # Ohne `CLAUDE_CONFIG_DIR` liegt die Datei neben, nicht in `~/.claude`.
    if is_default_dir(directory, home):
        return home / GLOBAL_CONFIG_FILE
    return directory / GLOBAL_CONFIG_FILE


def _read_identity(path: Path) -> tuple[str, str | None] | None:
    """``(accountUuid, emailAddress)`` aus der globalen CLI-Konfiguration."""
    for _ in range(IDENTITY_READ_ATTEMPTS):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            break
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError):
            time.sleep(IDENTITY_RETRY_SECONDS)
    else:
        logger.warning("accounts.identity_unreadable: %s", path.name)
        return None

    account = payload.get("oauthAccount") if isinstance(payload, dict) else None
    if not isinstance(account, dict):
        return None
    uuid = account.get("accountUuid")
    if not isinstance(uuid, str) or not uuid:
        return None
    email = account.get("emailAddress")
    return uuid, email if isinstance(email, str) and email else None


def _short_name(dirs: list[Path], email: str | None) -> str:
    """Der Ordnername ist der Name, den man dem Login selbst gegeben hat."""
    for directory in dirs:
        if directory.name != DEFAULT_DIR_NAME:
            return directory.name.removeprefix(DIR_PREFIX)
    if email:
        return email.split("@", 1)[0]
    return "claude"


def discover_claude_accounts(
    settings: Settings, home: Path | None = None
) -> list[ClaudeAccount]:
    """Ein Eintrag je Account, der Standardlogin zuerst.

    Der erste Eintrag erbt auch den Verlauf aus der Zeit vor der
    Mehr-Account-Unterstützung (siehe ``SnapshotStore.adopt_legacy``).
    """
    home = home or Path.home()
    grouped: dict[str, tuple[str | None, list[Path]]] = {}

    for directory in candidate_dirs(settings.claude_config_dirs, home):
        identity = _read_identity(_global_config_path(directory, home))
        account_id, email = identity if identity else (directory.name, None)
        _, dirs = grouped.setdefault(account_id, (email, []))
        dirs.append(directory)

    return [
        ClaudeAccount(
            info=AccountInfo(id=account_id, name=_short_name(dirs, email), email=email),
            config_dirs=tuple(dirs),
        )
        for account_id, (email, dirs) in grouped.items()
    ]
