"""Input widget with Ctrl-A select-all."""

from __future__ import annotations

from textual.binding import Binding
from textual.widgets import Input as TextualInput


class PromptInput(TextualInput):
    """A one-line input where Ctrl-A selects all instead of moving home."""

    BINDINGS = [
        Binding("ctrl+a", "select_all", "Select all", show=False),
    ]
