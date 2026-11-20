"""Status bar."""

from __future__ import annotations

from rich.markup import escape
from textual.widgets import Static

from ..models import LANGUAGE_LABELS


class StatusBar(Static):
    def __init__(self) -> None:
        super().__init__("", id="status-bar")

    def set_state(
        self,
        *,
        path: str | None,
        language: str | None,
        dirty: bool,
        mark_mode: bool,
        run_status: str,
        row: int,
        column: int,
    ) -> None:
        parts: list[str] = []
        if path:
            parts.append(escape(path) + (" ●" if dirty else ""))
        else:
            parts.append("No file")
        parts.append(LANGUAGE_LABELS.get(language, "Plain Text"))
        if mark_mode:
            parts.append("MARK")
        if run_status:
            parts.append(escape(run_status))
        parts.append(f"Ln {row + 1}, Col {column + 1}")
        self.update("  │  ".join(parts))
