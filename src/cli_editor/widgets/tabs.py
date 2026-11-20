"""The tab bar and editor stack."""

from __future__ import annotations

from textual import on
from textual.containers import Container
from textual.css.query import NoMatches
from textual.widgets import ContentSwitcher, Static, Tab, Tabs

from .editor import Editor


class EditorArea(Container):
    """Tabs plus a ContentSwitcher holding one Editor per tab."""

    def __init__(self) -> None:
        super().__init__(id="editor-area")

    def compose(self):
        yield Tabs(id="tabs")
        with ContentSwitcher(initial="empty", id="editors"):
            yield Static(
                "No file open — Ctrl-O to open",
                id="empty",
                classes="empty-editor",
            )

    @property
    def tabs(self) -> Tabs:
        return self.query_one("#tabs", Tabs)

    @property
    def editors(self) -> ContentSwitcher:
        return self.query_one("#editors", ContentSwitcher)

    async def add_editor(self, tab_id: str, label: str, editor: Editor) -> None:
        pane = Container(editor, id=tab_id)
        await self.editors.mount(pane)
        await self.tabs.add_tab(Tab(label, id=tab_id))
        self.tabs.active = tab_id
        self.editors.current = tab_id
        editor.focus()

    async def remove_editor(self, tab_id: str) -> None:
        await self.tabs.remove_tab(tab_id)
        try:
            pane = self.editors.query_one(f"#{tab_id}")
        except NoMatches:
            pass
        else:
            pane.remove()
        if self.tabs.tab_count == 0:
            self.editors.current = "empty"

    def activate(self, tab_id: str) -> None:
        self.tabs.active = tab_id
        self.editors.current = tab_id

    def set_label(self, tab_id: str, label: str) -> None:
        try:
            self.tabs.query_one(f"#{tab_id}", Tab).label = label
        except NoMatches:
            pass

    def editor_for(self, tab_id: str) -> Editor | None:
        try:
            pane = self.editors.query_one(f"#{tab_id}")
        except NoMatches:
            return None
        try:
            return pane.query_one(Editor)
        except NoMatches:
            return None

    @property
    def active_editor(self) -> Editor | None:
        current = self.editors.current
        if not current or current == "empty":
            return None
        return self.editor_for(current)

    @property
    def tab_ids(self) -> list[str]:
        return [tab.id for tab in self.tabs.query(Tab) if tab.id]

    @on(Tabs.TabActivated)
    def tab_activated(self, event: Tabs.TabActivated) -> None:
        if event.tab.id:
            self.editors.current = event.tab.id
            editor = self.editor_for(event.tab.id)
            if editor is not None:
                editor.focus()

    @on(Tabs.Cleared)
    def tabs_cleared(self) -> None:
        self.editors.current = "empty"
