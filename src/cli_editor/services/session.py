"""Session persistence."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from platformdirs import user_state_dir

from ..models import SessionState


def default_session_path() -> Path:
    return Path(user_state_dir("cliEditor")) / "session.json"


def load_session(path: Path | None = None) -> SessionState | None:
    session_path = path or default_session_path()
    try:
        data = json.loads(session_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        return SessionState.from_dict(data)
    except (TypeError, ValueError):
        return None


def save_session(state: SessionState, path: Path | None = None) -> None:
    session_path = path or default_session_path()
    session_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state.to_dict(), indent=2)
    handle, temporary = tempfile.mkstemp(
        prefix="session-", suffix=".json", dir=session_path.parent
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(payload)
        os.replace(temporary, session_path)
    except OSError:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
