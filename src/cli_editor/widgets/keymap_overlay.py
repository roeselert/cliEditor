"""The Ctrl-K keymap overlay."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

from ..keymap import KEYMAP_GROUPS


def keymap_markup() -> str:
    lines: list[str] = []
    for title, rows in KEYMAP_GROUPS:
        lines.append(f"[bold underline]{title}[/bold underline]")
        for key, description in rows:
            lines.append(f"  [cyan]{key:<30}[/cyan] {description}")
        lines.append("")
    return "\n".join(lines)


class KeymapScreen(ModalScreen[None]):
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("ctrl+k", "dismiss", "Close"),
        Binding("f1", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Container(id="keymap-container"):  # noqa: SIM117
            with VerticalScroll():
                yield Static(keymap_markup(), id="keymap-text")
