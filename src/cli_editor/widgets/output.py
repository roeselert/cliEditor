"""Bottom output panel for run results."""

from __future__ import annotations

from textual.containers import Container
from textual.widgets import Label, RichLog


class OutputPane(Container):
    def __init__(self) -> None:
        super().__init__(id="output-pane")

    def compose(self):
        yield Label("Output", id="output-title")
        yield RichLog(id="output", markup=False, highlight=False, wrap=True)

    def on_mount(self) -> None:
        self.display = False

    def show_output(self) -> None:
        self.display = True

    def hide_output(self) -> None:
        self.display = False

    def write(self, line: str) -> None:
        self.query_one("#output", RichLog).write(line)

    def clear(self) -> None:
        self.query_one("#output", RichLog).clear()

    def set_title(self, title: str) -> None:
        self.query_one("#output-title", Label).update(title)
