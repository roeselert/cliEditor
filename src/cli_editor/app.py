"""The cliEditor Textual application."""

from __future__ import annotations

import argparse
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.widgets import Footer, Static, Tabs
from textual.widgets.text_area import LanguageDoesNotExist, Selection

from .models import BufferState, SessionState, language_for_path
from .services.files import FileError, read_text, resolve_path, write_text
from .services.runner import Runner, RunnerError
from .services.session import load_session, save_session
from .widgets.editor import Editor
from .widgets.file_tree import FileTreePane
from .widgets.find_bar import FindBar
from .widgets.keymap_overlay import KeymapScreen
from .widgets.modals import (
    ConfirmScreen,
    ProjectFindScreen,
    PromptScreen,
    QuickOpenScreen,
    UnsavedScreen,
)
from .widgets.output import OutputPane
from .widgets.status_bar import StatusBar
from .widgets.tabs import EditorArea


class EditorApp(App[None]):
    """A small terminal code editor."""

    CSS_PATH = "cli_editor.tcss"
    ENABLE_COMMAND_PALETTE = False
    ESCAPE_TO_MINIMIZE = False
    TITLE = "cliEditor"

    BINDINGS = [
        Binding("ctrl+q", "quit_app", "Quit", priority=True),
        Binding("ctrl+n", "new_file", "New", priority=True),
        Binding("ctrl+o", "open_file", "Open", priority=True),
        Binding("ctrl+p", "quick_open", "Quick open", priority=True),
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("ctrl+shift+s", "save_as", "Save as", priority=True),
        Binding("f4", "save_as", "Save as", show=False),
        Binding("ctrl+w", "toggle_wrap", "Wrap", priority=True),
        Binding("ctrl+t,alt+w,ctrl+shift+w", "close_tab", "Close tab", priority=True),
        Binding("ctrl+tab", "next_tab", "Next tab", priority=True),
        Binding("ctrl+shift+tab", "previous_tab", "Previous tab", priority=True),
        Binding("alt+right", "next_tab", "Next tab", show=False),
        Binding("alt+left", "previous_tab", "Previous tab", show=False),
        Binding("ctrl+r", "run_file", "Run", priority=True),
        Binding("ctrl+l", "toggle_tree", "Toggle tree", priority=True),
        Binding("ctrl+k", "show_keymap", "Keymap", priority=True),
        Binding("f1", "show_keymap", "Keymap", priority=True),
        Binding("f6", "focus_next", "Next pane", priority=True),
        Binding("shift+f6", "focus_previous", "Previous pane", priority=True),
        Binding("ctrl+f", "find", "Find"),
        Binding("ctrl+shift+f", "project_find", "Find in files"),
        Binding("f3", "project_find", "Find in files", show=False),
        Binding("ctrl+g", "go_to_line", "Go to line"),
        Binding("ctrl+space", "toggle_mark", "Mark mode"),
        Binding("alt+m", "toggle_mark", "Mark mode", show=False),
        Binding("delete", "delete_file", "Delete file", show=False),
        Binding("f2", "rename_file", "Rename file", show=False),
        Binding("escape", "escape_action", "Stop / cancel", show=False),
    ]

    def __init__(
        self,
        root: Path | None = None,
        *,
        show_hidden: bool = False,
        use_session: bool = True,
    ) -> None:
        super().__init__()
        self.root = (root or Path.cwd()).expanduser().resolve()
        self.show_hidden = show_hidden
        self.use_session = use_session
        self.buffers: dict[Path, BufferState] = {}
        self.path_to_tab: dict[Path, str] = {}
        self.tab_paths: dict[str, Path] = {}
        self.editor_paths: dict[Editor, Path] = {}
        self.active_path: Path | None = None
        self._tab_counter = 0
        self.mark_mode = False
        self.line_wrap = False
        self.mark_anchor: tuple[int, int] = (0, 0)
        self.run_status = ""
        self.runner = Runner(self._run_line, self._run_done)

    # ------------------------------------------------------------------ compose

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            yield FileTreePane(self.root, self.show_hidden)
            with Vertical(id="right"):
                yield EditorArea()
                yield FindBar()
        yield OutputPane()
        yield StatusBar()
        yield Footer()
        yield Static(
            "Terminal too small\nResize to at least 20×20",
            id="too-small",
        )

    def _update_layout(self, size) -> None:
        small = size.height < 20 or size.width < 20
        self.screen.set_class(small, "-too-small")
        self.screen.set_class(size.height > size.width, "-portrait")

    def on_resize(self, event) -> None:
        self._update_layout(event.size)

    async def on_mount(self) -> None:
        self.sub_title = str(self.root)
        if self.use_session:
            await self.restore_session()
        self._update_layout(self.size)
        editor = self.editor_area.active_editor
        if editor is not None:
            editor.focus()
        elif self.tree_pane.display:
            self.tree_pane.focus_tree()
        self.update_status()

    def on_unmount(self) -> None:
        try:
            self.persist_session()
        except NoMatches:
            pass

    # ------------------------------------------------------------------ helpers

    @property
    def tree_pane(self) -> FileTreePane:
        return self.query_one(FileTreePane)

    @property
    def editor_area(self) -> EditorArea:
        return self.query_one(EditorArea)

    @property
    def find_bar(self) -> FindBar:
        return self.query_one(FindBar)

    @property
    def output(self) -> OutputPane:
        return self.query_one(OutputPane)

    @property
    def status_bar(self) -> StatusBar:
        return self.query_one(StatusBar)

    def editor_for_path(self, path: Path) -> Editor | None:
        tab_id = self.path_to_tab.get(path)
        return self.editor_area.editor_for(tab_id) if tab_id else None

    def is_dirty(self, path: Path) -> bool:
        editor = self.editor_for_path(path)
        buffer = self.buffers.get(path)
        if editor is None or buffer is None:
            return False
        return editor.text != buffer.saved_text

    def dirty_paths(self) -> list[Path]:
        return [path for path in self.buffers if self.is_dirty(path)]

    def tree_focused(self) -> bool:
        focused = self.focused
        return focused is not None and self.tree_pane in focused.ancestors_with_self

    @property
    def modal_open(self) -> bool:
        return len(self.screen_stack) > 1

    def update_status(self) -> None:
        editor = self.editor_area.active_editor
        path = self.active_path
        language = self.buffers[path].language if path in self.buffers else None
        dirty = self.is_dirty(path) if path else False
        row, column = editor.cursor_location if editor else (0, 0)
        display_path = None
        if path is not None:
            try:
                display_path = str(path.relative_to(self.root))
            except ValueError:
                display_path = str(path)
        self.status_bar.set_state(
            path=display_path,
            language=language,
            dirty=dirty,
            mark_mode=self.mark_mode,
            wrap=self.line_wrap,
            run_status=self.run_status,
            row=row,
            column=column,
        )

    def update_tab_label(self, path: Path) -> None:
        tab_id = self.path_to_tab.get(path)
        if not tab_id:
            return
        label = path.name
        if self.is_dirty(path):
            label = f"● {label}"
        self.editor_area.set_label(tab_id, label)

    # --------------------------------------------------------------- file opens

    async def open_path(
        self,
        path: Path,
        *,
        line: int | None = None,
        cursor: tuple[int, int] | None = None,
        scroll: tuple[int, int] | None = None,
        persist: bool = True,
    ) -> Editor | None:
        path = path.expanduser().resolve()
        existing = self.path_to_tab.get(path)
        if existing:
            self.editor_area.activate(existing)
            editor = self.editor_area.editor_for(existing)
            if editor is not None:
                if line is not None:
                    editor.move_cursor((line, 0), center=True)
                editor.focus()
            self.active_path = path
            self.update_status()
            return editor
        try:
            text = read_text(path)
        except FileError as error:
            self.notify(str(error), severity="error")
            return None

        self._tab_counter += 1
        tab_id = f"file-{self._tab_counter}"
        language = language_for_path(path)
        editor = None
        try:
            editor = Editor.code_editor(
                text=text,
                language=language,
                theme="monokai",
                soft_wrap=self.line_wrap,
                id=f"editor-{tab_id}",
            )
        except LanguageDoesNotExist:
            # Missing tree-sitter grammar/extra: keep editing as plain text.
            language = None
            editor = Editor(
                text=text,
                id=f"editor-{tab_id}",
                theme="monokai",
                show_line_numbers=True,
                soft_wrap=self.line_wrap,
                tab_behavior="indent",
            )
        editor.styles.overflow_x = "hidden" if self.line_wrap else "scroll"
        buffer = BufferState(
            path=path,
            language=language,
            saved_text=text,
            tab_id=tab_id,
        )
        self.buffers[path] = buffer
        self.path_to_tab[path] = tab_id
        self.tab_paths[tab_id] = path
        self.editor_paths[editor] = path
        await self.editor_area.add_editor(tab_id, path.name, editor)
        if cursor is not None:
            editor.move_cursor(cursor)
        if scroll is not None:
            editor.scroll_to(x=scroll[0], y=scroll[1], animate=False)
        if line is not None:
            editor.move_cursor((line, 0), center=True)
        self.active_path = path
        self.update_status()
        if persist:
            self.persist_session()
        return editor

    async def close_tab(self, tab_id: str, *, prompt: bool = True) -> bool:
        path = self.tab_paths.get(tab_id)
        if path is None:
            return False
        if prompt and self.is_dirty(path):
            choice = await self.push_screen_wait(
                UnsavedScreen(f"Save changes to {path.name}?")
            )
            if choice == "cancel":
                return False
            if choice == "save" and not self.save_path(path):
                return False
        await self.editor_area.remove_editor(tab_id)
        self.buffers.pop(path, None)
        self.path_to_tab.pop(path, None)
        self.tab_paths.pop(tab_id, None)
        for editor, editor_path in list(self.editor_paths.items()):
            if editor_path == path:
                self.editor_paths.pop(editor, None)
        current = self.editor_area.tabs.active
        self.active_path = self.tab_paths.get(current) if current else None
        self.update_status()
        self.persist_session()
        return True

    # --------------------------------------------------------------------- save

    def save_path(self, path: Path) -> bool:
        editor = self.editor_for_path(path)
        buffer = self.buffers.get(path)
        if editor is None or buffer is None:
            return False
        try:
            write_text(path, editor.text)
        except FileError as error:
            self.notify(str(error), severity="error")
            return False
        buffer.saved_text = editor.text
        self.update_tab_label(path)
        self.update_status()
        self.notify(f"Saved {path.name}")
        return True

    def save_active(self) -> bool:
        if self.active_path is None:
            return False
        return self.save_path(self.active_path)

    # ------------------------------------------------------------------ actions

    @work(exclusive=False)
    async def action_new_file(self) -> None:
        if self.modal_open:
            return
        value = await self.push_screen_wait(
            PromptScreen("New file path (relative to project root):", placeholder="src/new.py")
        )
        if not value:
            return
        path = resolve_path(self.root, value)
        if path.exists():
            self.notify(f"{path} already exists", severity="warning")
            return
        try:
            write_text(path, "", create_parents=True)
        except FileError as error:
            self.notify(str(error), severity="error")
            return
        await self.open_path(path)
        self.tree_pane.refresh_tree()

    @work(exclusive=False)
    async def action_open_file(self) -> None:
        if self.modal_open:
            return
        value = await self.push_screen_wait(
            PromptScreen("Open file path (relative to project root):", placeholder="src/app.py")
        )
        if value:
            await self.open_path(resolve_path(self.root, value))

    @work(exclusive=False)
    async def action_quick_open(self) -> None:
        if self.modal_open:
            return
        path = await self.push_screen_wait(QuickOpenScreen(self.root, self.show_hidden))
        if path is not None:
            await self.open_path(path)

    @work(exclusive=False)
    async def action_project_find(self) -> None:
        if self.modal_open:
            return
        result = await self.push_screen_wait(
            ProjectFindScreen(self.root, self.show_hidden)
        )
        if result is not None:
            path, line = result
            editor = await self.open_path(path, line=line)
            if editor is not None:
                editor.focus()

    async def action_save(self) -> None:
        if self.modal_open:
            return
        if not self.save_active():
            self.notify("Nothing to save", severity="warning")

    @work(exclusive=False)
    async def action_save_as(self) -> None:
        if self.modal_open:
            return
        if self.active_path is None:
            self.notify("No file open", severity="warning")
            return
        current = self.active_path
        try:
            initial = str(current.relative_to(self.root))
        except ValueError:
            initial = str(current)
        value = await self.push_screen_wait(
            PromptScreen(
                "Save as (relative to project root):",
                initial=initial,
            )
        )
        if not value:
            return
        new_path = resolve_path(self.root, value)
        if new_path.is_dir():
            self.notify("Target is a directory", severity="error")
            return
        if new_path != current and new_path in self.path_to_tab:
            self.notify("Target is already open in another tab", severity="warning")
            return
        editor = self.editor_area.active_editor
        buffer = self.buffers.get(current)
        if editor is None or buffer is None:
            return
        try:
            write_text(new_path, editor.text)
        except FileError as error:
            self.notify(str(error), severity="error")
            return
        tab_id = buffer.tab_id
        self.buffers.pop(current, None)
        self.path_to_tab.pop(current, None)
        buffer.path = new_path
        buffer.saved_text = editor.text
        new_language = language_for_path(new_path)
        try:
            editor.language = new_language
        except LanguageDoesNotExist:
            new_language = None
            editor.language = None
        buffer.language = new_language
        self.buffers[new_path] = buffer
        self.path_to_tab[new_path] = tab_id
        self.tab_paths[tab_id] = new_path
        self.editor_paths[editor] = new_path
        self.active_path = new_path
        self.update_tab_label(new_path)
        self.update_status()
        self.persist_session()
        self.tree_pane.refresh_tree()

    def action_toggle_wrap(self) -> None:
        if self.modal_open:
            return
        self.line_wrap = not self.line_wrap
        overflow_x = "hidden" if self.line_wrap else "scroll"
        for editor in self.editor_paths:
            editor.soft_wrap = self.line_wrap
            editor.styles.overflow_x = overflow_x
        active = self.editor_area.active_editor
        if active is not None:
            active.scroll_cursor_visible()
        self.update_status()

    @work(exclusive=False)
    async def action_close_tab(self) -> None:
        if self.modal_open:
            return
        tab_id = self.editor_area.tabs.active
        if tab_id:
            await self.close_tab(tab_id)

    @work(exclusive=False)
    async def action_quit_app(self) -> None:
        if self.modal_open:
            return
        dirty = self.dirty_paths()
        if dirty:
            choice = await self.push_screen_wait(
                UnsavedScreen(f"Save changes to {len(dirty)} file(s)?")
            )
            if choice == "cancel":
                return
            if choice == "save":
                for path in dirty:
                    if not self.save_path(path):
                        return
        self.persist_session()
        self.exit()

    async def action_run_file(self) -> None:
        if self.modal_open:
            return
        if self.active_path is None:
            self.notify("No file open", severity="warning")
            return
        if self.runner.running:
            self.notify("Already running", severity="warning")
            return
        if self.is_dirty(self.active_path) and not self.save_path(self.active_path):
            return
        self.output.clear()
        self.output.show_output()
        self.output.set_title(f"Output — {self.active_path.name}")
        self.run_status = "RUNNING"
        self.update_status()
        self.output.write(f"$ {self.active_path}")
        try:
            await self.runner.start(self.active_path)
        except RunnerError as error:
            self.run_status = ""
            self.output.write(str(error))
            self.notify(str(error), severity="error")
            self.update_status()

    def _run_line(self, line: str) -> None:
        self.output.write(line)

    def _run_done(self, code: int) -> None:
        if self.runner.stopped:
            self.run_status = "STOPPED"
            self.output.write("[stopped]")
        else:
            self.run_status = f"EXIT {code}"
            self.output.write(f"[exit {code}]")
        self.update_status()

    async def action_stop_run(self) -> None:
        await self.runner.stop()

    async def action_escape_action(self) -> None:
        if self.modal_open:
            return
        if self.runner.running:
            await self.runner.stop()
        elif self.mark_mode:
            self.cancel_mark_mode()

    def action_toggle_tree(self) -> None:
        if self.modal_open:
            return
        self.tree_pane.display = not self.tree_pane.display
        if not self.tree_pane.display:
            editor = self.editor_area.active_editor
            if editor is not None:
                editor.focus()
        self.persist_session()

    def action_show_keymap(self) -> None:
        if isinstance(self.screen, KeymapScreen):
            self.screen.dismiss(None)
            return
        if self.modal_open:
            return
        self.push_screen(KeymapScreen())

    def action_focus_next(self) -> None:
        if self.modal_open:
            return
        self.screen.focus_next()

    def action_focus_previous(self) -> None:
        if self.modal_open:
            return
        self.screen.focus_previous()

    def action_next_tab(self) -> None:
        if self.modal_open:
            return
        self.editor_area.tabs.action_next_tab()

    def action_previous_tab(self) -> None:
        if self.modal_open:
            return
        self.editor_area.tabs.action_previous_tab()

    def action_find(self) -> None:
        if self.modal_open:
            return
        focused = self.focused
        if focused is not None and self.tree_pane in focused.ancestors_with_self:
            self.tree_pane.show_filter()
            return
        editor = self.editor_area.active_editor
        if editor is not None:
            self.find_bar.open(editor)

    @work(exclusive=False)
    async def action_go_to_line(self) -> None:
        if self.modal_open:
            return
        editor = self.editor_area.active_editor
        if editor is None:
            return
        value = await self.push_screen_wait(
            PromptScreen("Go to line:", placeholder=str(editor.cursor_location[0] + 1))
        )
        if not value:
            return
        try:
            line = int(value)
        except ValueError:
            self.notify("Enter a line number", severity="error")
            return
        line = max(1, line) - 1
        editor.move_cursor((line, 0), center=True)
        editor.focus()

    def action_toggle_mark(self) -> None:
        if self.modal_open:
            return
        if self.mark_mode:
            self.cancel_mark_mode()
            return
        editor = self.editor_area.active_editor
        if editor is None:
            return
        self.mark_mode = True
        self.mark_anchor = editor.cursor_location
        self.update_status()

    def cancel_mark_mode(self) -> None:
        self.mark_mode = False
        editor = self.editor_area.active_editor
        if editor is not None:
            cursor = editor.cursor_location
            editor.selection = Selection(cursor, cursor)
        self.update_status()

    @work(exclusive=False)
    async def action_delete_file(self) -> None:
        if self.modal_open:
            return
        if not self.tree_focused():
            self.notify("Focus the file tree first", severity="warning")
            return
        path = self.tree_pane.selected_path()
        if path is None:
            self.notify("Select a file in the tree first", severity="warning")
            return
        if path.is_dir():
            self.notify("Directories can't be deleted", severity="warning")
            return
        if self.is_dirty(path):
            choice = await self.push_screen_wait(
                UnsavedScreen(f"Save changes to {path.name}?")
            )
            if choice == "cancel":
                return
            if choice == "save" and not self.save_path(path):
                return
        confirmed = await self.push_screen_wait(
            ConfirmScreen(f"Delete {path.name}? This cannot be undone.")
        )
        if not confirmed:
            return
        try:
            path.unlink()
        except OSError as error:
            self.notify(f"Cannot delete {path.name}: {error}", severity="error")
            return
        tab_id = self.path_to_tab.get(path)
        if tab_id:
            await self.close_tab(tab_id, prompt=False)
        self.tree_pane.refresh_tree()
        self.notify(f"Deleted {path.name}")

    @work(exclusive=False)
    async def action_rename_file(self) -> None:
        if self.modal_open:
            return
        if not self.tree_focused():
            self.notify("Focus the file tree first", severity="warning")
            return
        path = self.tree_pane.selected_path()
        if path is None:
            self.notify("Select a file in the tree first", severity="warning")
            return
        value = await self.push_screen_wait(
            PromptScreen("Rename file:", initial=path.name)
        )
        if not value or value == path.name:
            return
        if "/" in value or "\\" in value:
            self.notify("Use Save As to move a file", severity="error")
            return
        target = path.with_name(value)
        if target.exists():
            self.notify(f"{target.name} already exists", severity="error")
            return
        try:
            path.rename(target)
        except OSError as error:
            self.notify(f"Cannot rename: {error}", severity="error")
            return
        tab_id = self.path_to_tab.pop(path, None)
        buffer = self.buffers.pop(path, None)
        if tab_id and buffer:
            buffer.path = target
            buffer.language = language_for_path(target)
            self.buffers[target] = buffer
            self.path_to_tab[target] = tab_id
            self.tab_paths[tab_id] = target
            editor = self.editor_area.editor_for(tab_id)
            if editor is not None:
                editor.language = buffer.language
                self.editor_paths[editor] = target
            if self.active_path == path:
                self.active_path = target
            self.update_tab_label(target)
        self.tree_pane.refresh_tree()
        self.update_status()
        self.persist_session()

    # ------------------------------------------------------------------ events

    @on(Editor.Changed)
    def editor_changed(self, event: Editor.Changed) -> None:
        path = self.editor_paths.get(event.text_area)
        if path is None:
            return
        self.update_tab_label(path)
        self.update_status()

    @on(Editor.SelectionChanged)
    def selection_changed(self, event: Editor.SelectionChanged) -> None:
        if event.text_area is self.editor_area.active_editor:
            self.update_status()

    @on(Tabs.TabActivated)
    def tab_activated(self, event: Tabs.TabActivated) -> None:
        if event.tab.id:
            self.active_path = self.tab_paths.get(event.tab.id)
            self.update_status()

    # ---------------------------------------------------------------- session

    def persist_session(self) -> None:
        if not self.use_session:
            return
        tabs: list[dict] = []
        for tab_id in self.editor_area.tab_ids:
            path = self.tab_paths.get(tab_id)
            editor = self.editor_area.editor_for(tab_id)
            if path is None or editor is None:
                continue
            tabs.append(
                {
                    "path": str(path),
                    "cursor": list(editor.cursor_location),
                    "scroll": [editor.scroll_offset.x, editor.scroll_offset.y],
                }
            )
        width = self.tree_pane.size.width or 34
        state = SessionState(
            root=self.root,
            active=str(self.active_path) if self.active_path else None,
            tabs=tabs,
            tree_visible=self.tree_pane.display,
            tree_width=width,
        )
        try:
            save_session(state)
        except OSError:
            pass

    async def restore_session(self) -> None:
        state = load_session()
        if state is None:
            return
        try:
            if state.root.expanduser().resolve() != self.root:
                return
        except OSError:
            return
        if not state.tree_visible:
            self.tree_pane.display = False
        if state.tree_width:
            self.tree_pane.styles.width = state.tree_width
        active_tab: str | None = None
        for tab in state.tabs:
            path = Path(tab.get("path", "")).expanduser()
            if not path.exists():
                continue
            cursor = tab.get("cursor")
            scroll = tab.get("scroll")
            editor = await self.open_path(
                path,
                cursor=tuple(cursor) if cursor else None,
                scroll=tuple(scroll) if scroll else None,
                persist=False,
            )
            if editor is None:
                continue
            if state.active and path.resolve() == Path(state.active).expanduser().resolve():
                active_tab = self.path_to_tab.get(path.resolve())
        if active_tab:
            self.editor_area.activate(active_tab)
        self.update_status()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="cliEditor",
        description="A terminal code editor built with Textual.",
    )
    parser.add_argument("path", nargs="?", default=".", help="project root (default: .)")
    parser.add_argument("--hidden", action="store_true", help="show dotfiles in the tree")
    parser.add_argument("--no-session", action="store_true", help="don't restore or save a session")
    args = parser.parse_args(argv)
    app = EditorApp(
        Path(args.path),
        show_hidden=args.hidden,
        use_session=not args.no_session,
    )
    app.run()


app = EditorApp()
