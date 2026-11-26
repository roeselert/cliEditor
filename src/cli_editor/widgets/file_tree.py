"""The left-hand file tree with a filter mode."""

from __future__ import annotations

from pathlib import Path

from textual import events, on
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import DirectoryTree, Input, Tree

from ..services.files import iter_files
from .input import PromptInput


class ProjectTree(DirectoryTree):
    """Directory tree with Right to expand and Left to collapse a branch."""

    BINDINGS = [
        binding
        for binding in DirectoryTree.BINDINGS
        if getattr(binding, "key", None) not in {"left", "right"}
    ] + [
        Binding("right", "expand_cursor", "Open branch", show=False),
        Binding("left", "collapse_cursor", "Close branch", show=False),
    ]

    def action_expand_cursor(self) -> None:
        node = self.cursor_node
        if node is not None and node.allow_expand and not node.is_expanded:
            node.expand()

    def action_collapse_cursor(self) -> None:
        node = self.cursor_node
        if node is not None and node.allow_expand and node.is_expanded:
            node.collapse()


class FileTreePane(Container):
    """A DirectoryTree plus an input-driven filter tree."""

    def __init__(self, root: Path, show_hidden: bool = False) -> None:
        super().__init__(id="tree-pane")
        self.root_path = root
        self.show_hidden = show_hidden
        self.filter_visible = False

    def compose(self):
        yield PromptInput(placeholder="Filter files…", id="tree-filter")
        yield ProjectTree(self.root_path, id="tree")
        filter_tree: Tree[Path] = Tree("Matches", id="filter-tree")
        filter_tree.show_root = False
        yield filter_tree

    def on_mount(self) -> None:
        self.query_one("#tree-filter", Input).display = False
        self.query_one("#filter-tree", Tree).display = False

    @property
    def tree(self) -> ProjectTree:
        return self.query_one("#tree", ProjectTree)

    @property
    def filter_tree(self) -> Tree[Path]:
        return self.query_one("#filter-tree", Tree)

    def focus_tree(self) -> None:
        if self.filter_visible:
            self.filter_tree.focus()
        else:
            self.tree.focus()

    def show_filter(self) -> None:
        self.filter_visible = True
        filter_input = self.query_one("#tree-filter", Input)
        filter_input.display = True
        filter_input.value = ""
        filter_input.focus()

    def hide_filter(self, *, focus: bool = True) -> None:
        self.filter_visible = False
        self.query_one("#tree-filter", Input).display = False
        self.filter_tree.display = False
        self.tree.display = True
        if focus:
            self.tree.focus()

    def refresh_tree(self) -> None:
        self.tree.reload()
        if self.filter_visible:
            self.rebuild_filter(self.query_one("#tree-filter", Input).value)

    def rebuild_filter(self, query: str) -> None:
        filter_tree = self.filter_tree
        filter_tree.clear()
        filter_tree.show_root = False
        query = query.strip().lower()
        if not query:
            filter_tree.display = False
            self.tree.display = True
            return
        matches = [
            path
            for path in iter_files(self.root_path, include_hidden=self.show_hidden)
            if query in path.name.lower()
        ][:500]
        self.tree.display = False
        filter_tree.display = True
        if not matches:
            filter_tree.root.add_leaf("No matches", data=None)
        else:
            for path in matches:
                try:
                    label = str(path.relative_to(self.root_path))
                except ValueError:
                    label = str(path)
                filter_tree.root.add_leaf(label, data=path)
            filter_tree.move_cursor(filter_tree.root.children[0])
        filter_tree.root.expand()

    def selected_path(self) -> Path | None:
        if self.filter_visible and self.filter_tree.display:
            node = self.filter_tree.cursor_node
            data = node.data if node is not None else None
            if isinstance(data, Path):
                return data
            return None
        node = self.tree.cursor_node
        if node is None:
            return None
        return getattr(node.data, "path", None)

    @on(Input.Changed, "#tree-filter")
    def filter_changed(self, event: Input.Changed) -> None:
        self.rebuild_filter(event.value)

    @on(Input.Submitted, "#tree-filter")
    async def filter_submitted(self) -> None:
        if not self.filter_visible:
            return
        filter_input = self.query_one("#tree-filter", Input)
        if not filter_input.value.strip():
            return
        node = self.filter_tree.cursor_node
        data = node.data if node is not None else None
        if isinstance(data, Path) and data.is_file():
            editor = await self.app.open_path(data)  # type: ignore[attr-defined]
            if editor is not None:
                self.hide_filter(focus=False)
        else:
            self.filter_tree.focus()

    @on(DirectoryTree.FileSelected)
    async def file_selected(self, event: DirectoryTree.FileSelected) -> None:
        await self.app.open_path(event.path)  # type: ignore[attr-defined]

    @on(Tree.NodeSelected, "#filter-tree")
    async def filter_selected(self, event: Tree.NodeSelected) -> None:
        data = event.node.data
        if isinstance(data, Path) and data.is_file():
            await self.app.open_path(data)  # type: ignore[attr-defined]
            self.hide_filter(focus=False)

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape" and self.filter_visible:
            self.hide_filter()
            event.stop()
            return
        if self.filter_visible and self.query_one("#tree-filter", Input).has_focus:
            if event.key == "down":
                self.filter_tree.action_cursor_down()
                event.stop()
            elif event.key == "up":
                self.filter_tree.action_cursor_up()
                event.stop()
