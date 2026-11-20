"""Running the current file."""

from __future__ import annotations

import asyncio
import os
import shutil
import signal
import sys
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class RunnerError(Exception):
    """A user-facing run error."""


@dataclass
class RunCommand:
    argv: list[str] | None = None
    open_path: Path | None = None
    error: str = ""


def build_command(
    path: Path,
    *,
    python_executable: str | None = None,
    node_path: str | None = None,
) -> RunCommand:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return RunCommand(argv=[python_executable or sys.executable, "-u", str(path)])
    if suffix in {".js", ".mjs", ".cjs"}:
        node = node_path if node_path is not None else shutil.which("node")
        if not node:
            return RunCommand(error="node is not installed or not on PATH")
        return RunCommand(argv=[node, str(path)])
    if suffix in {".html", ".htm"}:
        return RunCommand(open_path=path)
    if suffix == ".css":
        return RunCommand(error="CSS files can't be run")
    return RunCommand(error=f"Don't know how to run {path.suffix or 'this file'}")


class Runner:
    """Streams a child process to callbacks on the app's event loop."""

    def __init__(
        self,
        on_line: Callable[[str], None],
        on_done: Callable[[int], None],
    ) -> None:
        self.on_line = on_line
        self.on_done = on_done
        self.process: asyncio.subprocess.Process | None = None
        self.stopped = False

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.returncode is None

    async def start(self, path: Path) -> None:
        if self.running:
            raise RunnerError("Already running")
        command = build_command(path)
        if command.error:
            raise RunnerError(command.error)
        if command.open_path is not None:
            webbrowser.open(command.open_path.as_uri())
            self.on_line(f"Opened {command.open_path.name} in the browser")
            self.on_done(0)
            return
        assert command.argv is not None
        self.stopped = False
        kwargs: dict = {}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(
                __import__("subprocess"), "CREATE_NEW_PROCESS_GROUP", 0
            )
        else:
            kwargs["start_new_session"] = True
        self.process = await asyncio.create_subprocess_exec(
            *command.argv,
            cwd=str(path.parent),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            **kwargs,
        )
        asyncio.create_task(self._pump())

    async def _pump(self) -> None:
        process = self.process
        if process is None or process.stdout is None:
            return
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            self.on_line(line.decode("utf-8", errors="replace").rstrip("\n"))
        code = await process.wait()
        self.process = None
        self.on_done(code)

    async def stop(self) -> None:
        process = self.process
        if process is None or process.returncode is not None:
            return
        self.stopped = True
        try:
            if os.name == "nt":
                process.terminate()
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
        except TimeoutError:
            try:
                if os.name == "nt":
                    process.kill()
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                process.kill()
            await process.wait()
