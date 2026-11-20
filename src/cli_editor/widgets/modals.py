"""Modal screens: prompts, confirmations, quick open, and project search."""

from __future__ import annotations

from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, OptionList, Static
from textual.widgets.option_list import Option

from ..services.files import (
    fuzzy_filter,
    iter_files,
    project_search,
)
from .input import PromptInput


class PromptScreen(ModalScreen[str | None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(
        self,
        message: str,
        *,
        initial: str = "",
        placeholder: str = "",
    ) -> None:
        super().__init__()
        self.message = message
        self.initial = initial
        self.placeholder = placeholder

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Static(self.message, classes="modal-title")
            yield PromptInput(
                value=self.initial,
                placeholder=self.placeholder,
                id="prompt-input",
            )
            yield Static("Enter to confirm · Esc to cancel", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#prompt-input", Input).focus()

    @on(Input.Submitted, "#prompt-input")
    def submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("escape", "cancel", "No"),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Static(self.message, classes="modal-title")
            with Horizontal(classes="modal-buttons"):
                yield Button("Delete", id="yes", variant="error")
                yield Button("Cancel", id="no")

    def on_mount(self) -> None:
        self.query_one("#no", Button).focus()

    @on(Button.Pressed, "#yes")
    def confirmed(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#no")
    def cancelled(self) -> None:
        self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class UnsavedScreen(ModalScreen[str]):
    BINDINGS = [
        Binding("s", "save", "Save"),
        Binding("d", "discard", "Discard"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Static(self.message, classes="modal-title")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", id="save", variant="primary")
                yield Button("Discard", id="discard", variant="warning")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#save", Button).focus()

    @on(Button.Pressed, "#save")
    def saved(self) -> None:
        self.dismiss("save")

    @on(Button.Pressed, "#discard")
    def discarded(self) -> None:
        self.dismiss("discard")

    @on(Button.Pressed, "#cancel")
    def cancelled(self) -> None:
        self.dismiss("cancel")

    def action_save(self) -> None:
        self.dismiss("save")

    def action_discard(self) -> None:
        self.dismiss("discard")

    def action_cancel(self) -> None:
        self.dismiss("cancel")


class QuickOpenScreen(ModalScreen[Path | None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, root: Path, show_hidden: bool = False) -> None:
        super().__init__()
        self.root = root
        self.show_hidden = show_hidden
        self.path_by_label: dict[str, Path] = {}
        self._all_labels: list[str] = []

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box wide"):
            yield Static("Quick open", classes="modal-title")
            yield PromptInput(placeholder="Type to filter files…", id="quick-input")
            yield OptionList(id="quick-options")

    def on_mount(self) -> None:
        for path in iter_files(self.root, include_hidden=self.show_hidden):
            try:
                label = str(path.relative_to(self.root))
            except ValueError:
                label = str(path)
            self.path_by_label[label] = path
            self._all_labels.append(label)
        self.query_one("#quick-input", Input).focus()
        self.refresh_options("")

    def refresh_options(self, query: str) -> None:
        options = self.query_one("#quick-options", OptionList)
        options.clear_options()
        labels = fuzzy_filter(query, self._all_labels, limit=100)
        if not labels:
            options.add_option(Option("No matches", disabled=True))
            return
        for label in labels:
            options.add_option(Option(label, id=label))
        options.highlighted = 0

    @on(Input.Changed, "#quick-input")
    def query_changed(self, event: Input.Changed) -> None:
        self.refresh_options(event.value)

    @on(Input.Submitted, "#quick-input")
    def submitted(self) -> None:
        self.open_highlighted()

    @on(OptionList.OptionSelected, "#quick-options")
    def option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id:
            self.dismiss(self.path_by_label.get(event.option.id))

    def open_highlighted(self) -> None:
        options = self.query_one("#quick-options", OptionList)
        if options.highlighted is None:
            return
        option = options.get_option_at_index(options.highlighted)
        if option.id:
            self.dismiss(self.path_by_label.get(option.id))

    def on_key(self, event) -> None:
        options = self.query_one("#quick-options", OptionList)
        if event.key == "down":
            options.action_cursor_down()
            event.stop()
        elif event.key == "up":
            options.action_cursor_up()
            event.stop()

    def action_cancel(self) -> None:
        self.dismiss(None)


class ProjectFindScreen(ModalScreen[tuple[Path, int] | None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, root: Path, show_hidden: bool = False) -> None:
        super().__init__()
        self.root = root
        self.show_hidden = show_hidden
        self.hit_by_id: dict[str, tuple[Path, int]] = {}

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box wide"):
            yield Static("Find across files", classes="modal-title")
            yield PromptInput(placeholder="Search project…", id="project-input")
            yield OptionList(id="project-options")

    def on_mount(self) -> None:
        self.query_one("#project-input", Input).focus()

    def search(self, query: str) -> None:
        options = self.query_one("#project-options", OptionList)
        options.clear_options()
        self.hit_by_id.clear()
        if not query:
            return
        hits = project_search(
            self.root,
            query,
            include_hidden=self.show_hidden,
        )
        if not hits:
            options.add_option(Option("No matches", disabled=True))
            return
        for index, hit in enumerate(hits):
            try:
                label = str(hit.path.relative_to(self.root))
            except ValueError:
                label = str(hit.path)
            option_id = f"hit-{index}"
            self.hit_by_id[option_id] = (hit.path, hit.line)
            options.add_option(
                Option(f"{label}:{hit.line + 1}: {hit.text[:100]}", id=option_id)
            )
        options.highlighted = 0

    @on(Input.Changed, "#project-input")
    def query_changed(self, event: Input.Changed) -> None:
        self.search(event.value)

    @on(Input.Submitted, "#project-input")
    def submitted(self) -> None:
        self.open_highlighted()

    @on(OptionList.OptionSelected, "#project-options")
    def option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id:
            self.dismiss(self.hit_by_id.get(event.option.id))

    def open_highlighted(self) -> None:
        options = self.query_one("#project-options", OptionList)
        if options.highlighted is None:
            return
        option = options.get_option_at_index(options.highlighted)
        if option.id:
            self.dismiss(self.hit_by_id.get(option.id))

    def on_key(self, event) -> None:
        options = self.query_one("#project-options", OptionList)
        if event.key == "down":
            options.action_cursor_down()
            event.stop()
        elif event.key == "up":
            options.action_cursor_up()
            event.stop()

    def action_cancel(self) -> None:
        self.dismiss(None)
