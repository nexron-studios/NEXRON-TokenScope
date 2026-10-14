"""Stößt die Anbieter-CLI an, wenn deren Zugriffstoken abgelaufen ist.

TokenScope erneuert Token grundsätzlich nicht selbst: Es liest keinen
``refresh_token`` und schreibt nie in die Credentials. Erneuern darf nur, wer
den Token ausgestellt hat – die CLI. Nach einem Neustart des Rechners ist der
Token regelmäßig abgelaufen, und bis dahin half nur, von Hand ein Terminal zu
öffnen. Dieses Modul nimmt genau diesen Handgriff ab.

Der Erfolg wird nicht geglaubt, sondern geprüft: Der Poller fragt den Anbieter
nach dem Kommando genau einmal erneut ab. Bleibt es bei ``auth_expired``, hat
das Kommando den Token nicht erneuert – das steht dann so im Log, statt still
alle fünf Minuten wiederholt zu werden.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from .config import Settings
from .normalize import now

logger = logging.getLogger(__name__)

#: Ein Konsolenfenster darf auf dem Kiosk nicht aufblitzen.
_CREATE_NO_WINDOW = 0x0800_0000

#: Windows-Endungen, die nur die Kommandozeile selbst starten kann.
_SHIM_SUFFIXES = frozenset({".cmd", ".bat"})


def resolve_command(command: list[str]) -> list[str] | None:
    """Macht aus einem Kommandonamen etwas, das sich wirklich starten lässt.

    ``claude`` und ``npx`` sind auf Windows ``.cmd``-Shims aus npm.
    ``create_subprocess_exec`` startet die nicht – es braucht den aufgelösten
    Pfad, und Shims müssen über ``cmd /c`` laufen. Ohne das scheitert jeder
    Aufruf mit einem nichtssagenden ``FileNotFoundError``.
    """
    if not command:
        return None

    resolved = shutil.which(command[0])
    if resolved is None:
        return None

    if sys.platform == "win32" and Path(resolved).suffix.lower() in _SHIM_SUFFIXES:
        comspec = shutil.which("cmd") or "cmd.exe"
        return [comspec, "/c", resolved, *command[1:]]

    return [resolved, *command[1:]]


def _spawn_kwargs() -> dict[str, int]:
    if sys.platform == "win32":
        return {"creationflags": _CREATE_NO_WINDOW}
    return {}


async def run_quiet(
    command: list[str], *, timeout: float, env: dict[str, str] | None = None
) -> tuple[int, bytes] | None:
    """Führt ein Kommando aus und gibt ``(Rückgabewert, stdout)`` zurück.

    ``None`` heißt: gar nicht erst gelaufen. Wirft nie – ein kaputtes Kommando
    darf weder den Poller noch einen Abruf beschädigen.
    """
    resolved = resolve_command(command)
    if resolved is None:
        logger.warning("cli.command_not_found", extra={"command": command[:1]})
        return None

    process = None
    try:
        process = await asyncio.create_subprocess_exec(
            *resolved,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            stdin=asyncio.subprocess.DEVNULL,
            env={**os.environ, **env} if env else None,
            **_spawn_kwargs(),
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("cli.timeout: %s nach %.0f s", command[0], timeout)
        if process is not None:
            process.kill()
        return None
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        logger.warning("cli.spawn_failed: %s (%s)", command[0], exc)
        return None

    return process.returncode or 0, stdout or b""


class CliRefresher:
    """Hält fest, wann welche CLI zuletzt angestoßen wurde.

    Gezählt wird je Kachel (``scope_key``), nicht je Anbieter: Zwei
    Claude-Logins laufen unabhängig voneinander ab.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._last_attempt_at: dict[str, datetime] = {}
        self._running: set[str] = set()

    def command_for(self, key: str) -> list[str]:
        commands = {
            "claude": self._settings.claude_cli_refresh_command,
            "codex": self._settings.codex_cli_refresh_command,
        }
        provider_id = key.split(":", 1)[0]
        return list(commands.get(provider_id) or [])

    def may_attempt(self, key: str) -> bool:
        """Ob ein Anstoß jetzt erlaubt ist – Kommando da, Sperre abgelaufen."""
        if not self.command_for(key):
            return False
        if key in self._running:
            return False

        last = self._last_attempt_at.get(key)
        if last is None:
            return True

        gap = self._settings.cli_refresh_min_interval_seconds
        return now() - last >= timedelta(seconds=gap)

    async def trigger(self, key: str, env: dict[str, str] | None = None) -> bool:
        """Startet das Kommando einmal. ``True`` heißt nur: sauber beendet.

        ``env`` setzt etwa ``CLAUDE_CONFIG_DIR``, damit die CLI den Token
        genau dieses Logins erneuert.
        """
        command = self.command_for(key)
        if not command:
            return False

        self._last_attempt_at[key] = now()
        self._running.add(key)
        try:
            logger.info("cli.refresh_triggered: %s (%s)", key, command[0])
            outcome = await run_quiet(
                command, timeout=self._settings.cli_refresh_timeout_seconds, env=env
            )
        finally:
            self._running.discard(key)

        if outcome is None:
            return False

        code, _ = outcome
        if code != 0:
            logger.warning("cli.refresh_failed: %s endete mit %d", key, code)
            return False

        return True
