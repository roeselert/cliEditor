"""The editor widget, with cliEditor's key overrides."""

from __future__ import annotations

from textual.binding import Binding
from textual.widgets import TextArea


class Editor(TextArea):
    """A TextArea that cooperates with mark mode and app-level shortcuts."""

    BINDINGS = [
        binding
        for binding in TextArea.BINDINGS
        if binding.key not in {"ctrl+k", "home,ctrl+a", "ctrl+w,ctrl+backspace,alt+backspace"}
    ] + [
        Binding("home", "cursor_line_start", "Line start", show=False),
        Binding("ctrl+a", "select_all", "Select all", show=False),
        Binding("ctrl+backspace,alt+backspace", "delete_word_left", "Delete word", show=False),
        Binding(
            "alt+k",
            "delete_to_end_of_line_or_delete_line",
            "Delete to end of line",
            show=False,
        ),
    ]

    @property
    def marking(self) -> bool:
        return bool(getattr(self.app, "mark_mode", False))

    def action_cursor_up(self, select: bool = False) -> None:
        super().action_cursor_up(select or self.marking)

    def action_cursor_down(self, select: bool = False) -> None:
        super().action_cursor_down(select or self.marking)

    def action_cursor_left(self, select: bool = False) -> None:
        super().action_cursor_left(select or self.marking)

    def action_cursor_right(self, select: bool = False) -> None:
        super().action_cursor_right(select or self.marking)

    def action_cursor_word_left(self, select: bool = False) -> None:
        super().action_cursor_word_left(select or self.marking)

    def action_cursor_word_right(self, select: bool = False) -> None:
        super().action_cursor_word_right(select or self.marking)

    def action_cursor_line_start(self, select: bool = False) -> None:
        super().action_cursor_line_start(select or self.marking)

    def action_cursor_line_end(self, select: bool = False) -> None:
        super().action_cursor_line_end(select or self.marking)

    def action_cursor_page_up(self, select: bool = False) -> None:
        super().action_cursor_page_up(select or self.marking)

    def action_cursor_page_down(self, select: bool = False) -> None:
        super().action_cursor_page_down(select or self.marking)

    def action_copy(self) -> None:
        super().action_copy()
        if self.marking:
            self.app.cancel_mark_mode()  # type: ignore[attr-defined]

    async def _on_key(self, event) -> None:
        # TextArea's indent mode uses Escape to move focus. Let Escape cancel
        # mark mode or stop a run instead.
        if event.key == "escape":
            runner = getattr(self.app, "runner", None)
            if getattr(self.app, "mark_mode", False) or (
                runner is not None and runner.running
            ):
                await self.app.action_escape_action()  # type: ignore[attr-defined]
                event.stop()
                event.prevent_default()
                return
        await super()._on_key(event)

    def on_mouse_down(self, event) -> None:
        if self.marking:
            self.app.cancel_mark_mode()  # type: ignore[attr-defined]
