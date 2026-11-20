"""In-file find bar."""

from __future__ import annotations

from textual import on
from textual.containers import Container
from textual.widgets import Input, Static
from textual.widgets.text_area import Selection

from ..services.files import find_matches
from .editor import Editor
from .input import PromptInput


class FindBar(Container):
    def __init__(self) -> None:
        super().__init__(id="find-bar")
        self.editor: Editor | None = None
        self.matches: list[tuple[int, int]] = []
        self.index = -1

    def compose(self):
        yield PromptInput(placeholder="Find in file…", id="find-input")
        yield Static("0/0", id="find-count")

    def on_mount(self) -> None:
        self.display = False

    def open(self, editor: Editor) -> None:
        self.editor = editor
        self.display = True
        find_input = self.query_one("#find-input", Input)
        find_input.value = ""
        find_input.focus()
        self.matches = []
        self.index = -1
        self.query_one("#find-count", Static).update("0/0")

    def close(self) -> None:
        self.display = False
        if self.editor is not None:
            cursor = self.editor.cursor_location
            self.editor.selection = Selection(cursor, cursor)
            self.editor.focus()

    def _select(self, index: int) -> None:
        if self.editor is None or not self.matches:
            return
        self.index = index % len(self.matches)
        row, column = self.matches[self.index]
        length = len(self.query_one("#find-input", Input).value)
        self.editor.selection = Selection((row, column), (row, column + length))
        self.editor.scroll_cursor_visible()
        self.query_one("#find-count", Static).update(
            f"{self.index + 1}/{len(self.matches)}"
        )

    @on(Input.Changed, "#find-input")
    def query_changed(self, event: Input.Changed) -> None:
        if self.editor is None:
            return
        self.matches = find_matches(self.editor.text, event.value)
        self.index = -1
        self.query_one("#find-count", Static).update(f"0/{len(self.matches)}")
        if self.matches:
            self._select(0)

    @on(Input.Submitted, "#find-input")
    def next_match(self) -> None:
        if self.matches:
            self._select(self.index + 1)

    def previous_match(self) -> None:
        if self.matches:
            self._select(self.index - 1)

    def on_key(self, event) -> None:
        if not self.display:
            return
        if event.key == "escape":
            self.close()
            event.stop()
        elif event.key == "shift+enter":
            self.previous_match()
            event.stop()
