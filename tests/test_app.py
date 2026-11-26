from pathlib import Path

from textual import events
from textual.widgets import Input, RichLog, Static, Tab

from cli_editor.app import EditorApp
from cli_editor.widgets.keymap_overlay import KeymapScreen
from cli_editor.widgets.modals import (
    ConfirmScreen,
    ProjectFindScreen,
    PromptScreen,
    QuickOpenScreen,
    UnsavedScreen,
)


async def start_app(root: Path) -> EditorApp:
    return EditorApp(root, use_session=False)


async def wait_until(pilot, predicate, attempts: int = 100) -> None:
    for _ in range(attempts):
        if predicate():
            return
        await pilot.pause(0.05)
    raise AssertionError("condition was not met")


async def test_open_save_and_dirty_tab(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_text("print('hi')\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        editor = await app.open_path(path)
        assert editor is not None
        assert app.editor_area.tab_ids == ["file-1"]
        assert editor.text == "print('hi')\n"
        assert editor.theme == "monokai"

        editor.insert("x")
        await pilot.pause()
        assert app.is_dirty(path)
        tab = app.editor_area.tabs.query_one("#file-1", Tab)
        assert str(tab.label).startswith("●")

        await pilot.press("ctrl+s")
        await pilot.pause()
        assert app.is_dirty(path) is False
        assert path.read_text(encoding="utf-8").startswith("x")
        assert not str(tab.label).startswith("●")


async def test_editor_background_is_dark(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_text("x\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        editor = await app.open_path(path)
        assert editor is not None
        background = editor.styles.background
        assert background is not None
        assert background.a == 1
        red, green, blue = background.rgb
        assert max(red, green, blue) < 60

        text_color = editor.styles.color
        assert text_color is not None
        text_red, text_green, text_blue = text_color.rgb
        assert max(text_red, text_green, text_blue) > 180

        screen_background = app.screen.styles.background
        assert screen_background is not None
        assert screen_background.a == 1
        assert max(screen_background.rgb) < 60

        tree_background = app.tree_pane.tree.styles.background
        assert tree_background is not None
        assert tree_background.a == 1
        assert max(tree_background.rgb) < 60

        await pilot.press("ctrl+k")
        await pilot.pause()
        assert isinstance(app.screen, KeymapScreen)


async def test_editor_vertical_scrolling(tmp_path: Path) -> None:
    path = tmp_path / "long.py"
    path.write_text("\n".join(f"line {index}" for index in range(100)) + "\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(100, 25)) as pilot:
        await pilot.pause()
        editor = await app.open_path(path)
        assert editor is not None
        await pilot.pause()

        assert editor.show_vertical_scrollbar is True
        assert editor.styles.overflow_y == "scroll"
        assert editor.styles.scrollbar_size_vertical >= 1

        before = editor.scroll_offset.y
        editor.post_message(
            events.MouseScrollDown(editor, 10, 5, 0, 3, 0, False, False, False)
        )
        await pilot.pause()
        assert editor.scroll_offset.y > before

        scrolled = editor.scroll_offset.y
        editor.post_message(
            events.MouseScrollUp(editor, 10, 5, 0, -3, 0, False, False, False)
        )
        await pilot.pause()
        assert editor.scroll_offset.y < scrolled


async def test_editor_horizontal_scrolling(tmp_path: Path) -> None:
    path = tmp_path / "wide.py"
    path.write_text("x" * 500 + "\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(100, 25)) as pilot:
        await pilot.pause()
        editor = await app.open_path(path)
        assert editor is not None
        await pilot.pause()

        assert editor.show_horizontal_scrollbar is True
        assert editor.styles.overflow_x == "scroll"
        assert editor.styles.scrollbar_size_horizontal == 1

        before = editor.scroll_offset.x
        editor.post_message(
            events.MouseScrollRight(editor, 10, 5, 3, 0, 0, False, False, False)
        )
        await pilot.pause()
        assert editor.scroll_offset.x > before

        scrolled = editor.scroll_offset.x
        editor.post_message(
            events.MouseScrollLeft(editor, 10, 5, -3, 0, 0, False, False, False)
        )
        await pilot.pause()
        assert editor.scroll_offset.x < scrolled


async def test_open_all_mvp_languages(tmp_path: Path) -> None:
    files = {
        "a.py": "python",
        "b.js": "javascript",
        "c.html": "html",
        "d.css": "css",
    }
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        for name, language in files.items():
            path = tmp_path / name
            path.write_text("x\n", encoding="utf-8")
            editor = await app.open_path(path)
            assert editor is not None
            assert editor.language == language
            assert app.buffers[path].language == language


async def test_update_status_survives_unmounted_dom(tmp_path: Path) -> None:
    # Queued TabActivated/Changed messages can be delivered during shutdown,
    # after the EditorArea has been removed. Status updates must not raise.
    app = await start_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.editor_area.remove()
        await pilot.pause()
        app.update_status()


async def test_tabs_switch_and_close(tmp_path: Path) -> None:
    first = tmp_path / "a.py"
    second = tmp_path / "b.py"
    first.write_text("a\n", encoding="utf-8")
    second.write_text("b\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await app.open_path(first)
        await app.open_path(second)
        assert app.active_path == second

        await pilot.press("ctrl+tab")
        await pilot.pause()
        assert app.active_path == first

        await pilot.press("ctrl+t")
        await pilot.pause()
        assert app.editor_area.tab_ids == ["file-2"]
        assert app.active_path == second

        await pilot.press("ctrl+t")
        await pilot.pause()
        assert app.editor_area.tab_ids == []
        assert app.active_path is None


async def test_ctrl_w_toggles_line_wrap(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_text("x" * 200 + "\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(100, 25)) as pilot:
        await pilot.pause()
        editor = await app.open_path(path)
        assert editor is not None
        await pilot.pause()

        assert editor.soft_wrap is False
        assert editor.styles.overflow_x == "scroll"
        assert app.line_wrap is False

        await pilot.press("ctrl+w")
        await pilot.pause()
        assert editor.soft_wrap is True
        assert editor.styles.overflow_x == "hidden"
        assert app.line_wrap is True
        assert app.editor_area.tab_ids == ["file-1"]
        assert "WRAP" in str(app.status_bar.content)

        second = tmp_path / "b.py"
        second.write_text("y\n", encoding="utf-8")
        second_editor = await app.open_path(second)
        assert second_editor is not None
        await pilot.pause()
        assert second_editor.soft_wrap is True
        assert second_editor.styles.overflow_x == "hidden"

        await pilot.press("ctrl+w")
        await pilot.pause()
        assert editor.soft_wrap is False
        assert editor.styles.overflow_x == "scroll"
        assert second_editor.soft_wrap is False
        assert second_editor.styles.overflow_x == "scroll"
        assert app.line_wrap is False
        assert "WRAP" not in str(app.status_bar.content)


async def test_inactive_tab_text_is_readable(tmp_path: Path) -> None:
    first = tmp_path / "a.py"
    second = tmp_path / "b.py"
    first.write_text("a\n", encoding="utf-8")
    second.write_text("b\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await app.open_path(first)
        await app.open_path(second)
        await pilot.pause()

        tabs = app.editor_area.tabs
        inactive = tabs.get_tab("file-1")
        active = tabs.get_tab("file-2")
        assert inactive is not None
        assert active is not None
        assert inactive.rich_style.color == active.rich_style.color
        assert inactive.rich_style.bgcolor != active.rich_style.bgcolor


async def test_find_bar_cycles_matches(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_text("hello world\nsecond hello\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        editor = await app.open_path(path)
        assert editor is not None
        editor.focus()
        await pilot.press("ctrl+f")
        await pilot.pause()
        assert app.find_bar.display is True

        await pilot.press("h", "e", "l", "l", "o")
        await pilot.pause()
        assert len(app.find_bar.matches) == 2
        assert editor.selected_text == "hello"
        assert app.find_bar.index == 0

        await pilot.press("enter")
        await pilot.pause()
        assert app.find_bar.index == 1

        await pilot.press("escape")
        await pilot.pause()
        assert app.find_bar.display is False


async def test_mark_mode_extends_selection_and_copy_exits(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_text("hello\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        editor = await app.open_path(path)
        assert editor is not None
        editor.move_cursor((0, 0))
        await pilot.press("ctrl+space")
        await pilot.pause()
        assert app.mark_mode is True

        await pilot.press("right", "right")
        await pilot.pause()
        assert editor.selected_text == "he"

        await pilot.press("ctrl+c")
        await pilot.pause()
        assert app.mark_mode is False


async def test_escape_cancels_mark_mode(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_text("hello\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        editor = await app.open_path(path)
        assert editor is not None
        editor.move_cursor((0, 0))
        await pilot.press("ctrl+space")
        await pilot.press("right", "right")
        await pilot.pause()
        assert app.mark_mode is True
        await pilot.press("escape")
        await pilot.pause()
        assert app.mark_mode is False
        assert editor.selected_text == ""


async def test_tree_enter_and_filter_open_files(tmp_path: Path) -> None:
    first = tmp_path / "a.py"
    second = tmp_path / "b.css"
    first.write_text("a\n", encoding="utf-8")
    second.write_text("b {}\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        tree = app.tree_pane.tree
        node = next(
            child
            for child in tree.root.children
            if getattr(child.data, "path", None) == first
        )
        tree.move_cursor(node)
        tree.focus()
        await pilot.press("enter")
        await pilot.pause()
        assert app.active_path == first

        tree.focus()
        await pilot.press("ctrl+f")
        await pilot.pause()
        assert app.tree_pane.filter_visible is True
        await pilot.press("b", ".", "c", "s", "s")
        await pilot.pause()
        assert app.query_one("#tree-filter", Input).value == "b.css"
        assert app.tree_pane.filter_tree.cursor_node is not None
        assert app.tree_pane.filter_tree.cursor_node.data == second

        await pilot.press("enter")
        await pilot.pause()
        assert app.active_path == second
        assert app.tree_pane.filter_visible is False


async def test_tree_right_expands_and_left_collapses(tmp_path: Path) -> None:
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "x.py").write_text("x\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("a\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        tree = app.tree_pane.tree
        tree.focus()
        await pilot.pause()

        await pilot.press("down")
        await pilot.pause()
        node = tree.cursor_node
        assert node is not None
        assert str(node.label) == "sub"
        assert node.allow_expand is True
        assert node.is_expanded is False

        await pilot.press("right")
        await pilot.pause()
        assert node.is_expanded is True

        await pilot.press("left")
        await pilot.pause()
        assert node.is_expanded is False

        # A file is not a branch, so both arrows are no-ops.
        file_node = next(
            child
            for child in tree.root.children
            if getattr(child.data, "path", None) == tmp_path / "a.py"
        )
        tree.move_cursor(file_node)
        await pilot.press("left")
        await pilot.press("right")
        await pilot.pause()
        assert tree.cursor_node is file_node
        assert file_node.is_expanded is False


async def test_quick_open(tmp_path: Path) -> None:
    first = tmp_path / "a.py"
    second = tmp_path / "b.css"
    first.write_text("a\n", encoding="utf-8")
    second.write_text("b {}\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("ctrl+p")
        await pilot.pause()
        assert isinstance(app.screen, QuickOpenScreen)

        await pilot.press("b", ".", "c", "s", "s")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.active_path == second


async def test_project_find_opens_hit(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_text("first\nneedle here\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("ctrl+shift+f")
        await pilot.pause()
        assert isinstance(app.screen, ProjectFindScreen)

        await pilot.press("n", "e", "e", "d", "l", "e")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.active_path == path
        editor = app.editor_area.active_editor
        assert editor is not None
        assert editor.cursor_location[0] == 1


async def test_open_by_path_and_go_to_line(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_text("one\ntwo\nthree\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("ctrl+o")
        await pilot.pause()
        assert isinstance(app.screen, PromptScreen)
        await pilot.press("a", ".", "p", "y")
        await pilot.press("enter")
        await pilot.pause()
        assert app.active_path == path

        await pilot.press("ctrl+g")
        await pilot.pause()
        assert isinstance(app.screen, PromptScreen)
        await pilot.press("3")
        await pilot.press("enter")
        await pilot.pause()
        editor = app.editor_area.active_editor
        assert editor is not None
        assert editor.cursor_location[0] == 2


async def test_save_as_and_new_file(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_text("a\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        editor = await app.open_path(path)
        assert editor is not None
        editor.insert("x")
        await pilot.press("f4")
        await pilot.pause()
        assert isinstance(app.screen, PromptScreen)

        await pilot.press("ctrl+a")
        await pilot.press("c", "o", "p", "y", ".", "p", "y")
        await pilot.press("enter")
        await pilot.pause()
        copy = tmp_path / "copy.py"
        assert copy.is_file()
        assert app.active_path == copy

        await pilot.press("ctrl+n")
        await pilot.pause()
        assert isinstance(app.screen, PromptScreen)
        await pilot.press("n", "e", "w", ".", "p", "y")
        await pilot.press("enter")
        await pilot.pause()
        assert (tmp_path / "new.py").is_file()
        assert app.active_path == tmp_path / "new.py"


async def test_save_as_refuses_target_open_in_another_tab(tmp_path: Path) -> None:
    first = tmp_path / "a.py"
    second = tmp_path / "b.py"
    first.write_text("a\n", encoding="utf-8")
    second.write_text("b\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await app.open_path(first)
        await app.open_path(second)
        assert app.active_path == second

        await pilot.press("f4")
        await pilot.pause()
        assert isinstance(app.screen, PromptScreen)
        await pilot.press("ctrl+a")
        await pilot.press("a", ".", "p", "y")
        await pilot.press("enter")
        await pilot.pause()

        assert app.active_path == second
        assert app.path_to_tab[first] == "file-1"
        assert app.path_to_tab[second] == "file-2"
        assert first.read_text(encoding="utf-8") == "a\n"


async def test_rename_and_delete_from_tree(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_text("a\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        tree = app.tree_pane.tree
        node = next(
            child
            for child in tree.root.children
            if getattr(child.data, "path", None) == path
        )
        tree.move_cursor(node)
        tree.focus()
        await pilot.pause()

        await pilot.press("f2")
        await pilot.pause()
        assert isinstance(app.screen, PromptScreen)
        await pilot.press("ctrl+a")
        await pilot.press("r", "e", "n", "a", "m", "e", "d", ".", "p", "y")
        await pilot.press("enter")
        await pilot.pause()
        renamed = tmp_path / "renamed.py"
        assert renamed.is_file()

        await pilot.pause(0.1)
        node = next(
            child
            for child in tree.root.children
            if getattr(child.data, "path", None) == renamed
        )
        tree.move_cursor(node)
        tree.focus()
        await pilot.press("delete")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press("y")
        await pilot.pause()
        assert not renamed.exists()


async def test_dirty_close_prompts(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_text("x\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        editor = await app.open_path(path)
        assert editor is not None
        editor.insert("y")
        await pilot.pause()

        await pilot.press("ctrl+t")
        await pilot.pause()
        assert isinstance(app.screen, UnsavedScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert app.editor_area.tab_ids == ["file-1"]
        assert app.is_dirty(path)

        await pilot.press("alt+w")
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()
        assert app.editor_area.tab_ids == []
        assert path.read_text(encoding="utf-8").startswith("y")


async def test_run_python_file_streams_output(tmp_path: Path) -> None:
    path = tmp_path / "run.py"
    path.write_text("print('RUNOK')\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await app.open_path(path)
        await pilot.press("ctrl+r")
        await wait_until(
            pilot,
            lambda: app.run_status.startswith("EXIT") and not app.runner.running,
        )
        output = app.output.query_one("#output", RichLog)
        assert any("RUNOK" in str(line) for line in output.lines)
        assert app.run_status == "EXIT 0"


async def test_keymap_overlay(tmp_path: Path) -> None:
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("ctrl+k")
        await pilot.pause()
        assert isinstance(app.screen, KeymapScreen)
        await pilot.press("ctrl+k")
        await pilot.pause()
        assert not isinstance(app.screen, KeymapScreen)


async def test_cut_paste_undo_redo(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_text("abc\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        editor = await app.open_path(path)
        assert editor is not None
        editor.move_cursor((0, 0))
        await pilot.press("ctrl+a")
        await pilot.pause()
        assert editor.selected_text == "abc\n"

        await pilot.press("ctrl+x")
        await pilot.pause()
        assert editor.text == ""
        await pilot.press("ctrl+v")
        await pilot.pause()
        assert editor.text == "abc\n"

        await pilot.press("ctrl+z")
        await pilot.pause()
        assert editor.text == ""
        await pilot.press("ctrl+y")
        await pilot.pause()
        assert editor.text == "abc\n"


async def test_escape_stops_running_file(tmp_path: Path) -> None:
    path = tmp_path / "slow.py"
    path.write_text(
        "import time\nprint('STARTED', flush=True)\ntime.sleep(30)\n",
        encoding="utf-8",
    )
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await app.open_path(path)
        await pilot.press("ctrl+r")
        await wait_until(pilot, lambda: app.runner.running)
        await pilot.press("escape")
        await wait_until(pilot, lambda: not app.runner.running)
        assert app.run_status == "STOPPED"


async def test_small_terminal_shows_message(tmp_path: Path) -> None:
    app = await start_app(tmp_path)
    async with app.run_test(size=(50, 15)) as pilot:
        await pilot.pause()
        assert app.screen.has_class("-too-small")
        assert app.query_one("#too-small", Static).display is True


async def test_missing_syntax_falls_back_to_plain_text(
    tmp_path: Path, monkeypatch
) -> None:
    from textual.widgets.text_area import LanguageDoesNotExist

    from cli_editor.widgets.editor import Editor

    def missing(cls, *args, **kwargs):
        raise LanguageDoesNotExist("python")

    monkeypatch.setattr(Editor, "code_editor", classmethod(missing))
    path = tmp_path / "a.py"
    path.write_text("print('x')\n", encoding="utf-8")
    app = await start_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        editor = await app.open_path(path)
        assert editor is not None
        assert editor.language is None
        assert editor.text == "print('x')\n"
        assert app.buffers[path].language is None


async def test_landscape_terminal_layout_is_supported(tmp_path: Path) -> None:
    app = await start_app(tmp_path)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        assert not app.screen.has_class("-portrait")
        assert not app.screen.has_class("-too-small")


async def test_portrait_terminal_layout_is_supported(tmp_path: Path) -> None:
    app = await start_app(tmp_path)
    async with app.run_test(size=(40, 60)) as pilot:
        await pilot.pause()
        assert app.screen.has_class("-portrait")
        assert not app.screen.has_class("-too-small")


async def test_session_restores_tabs_and_cursor(tmp_path: Path, monkeypatch) -> None:
    state_dir = tmp_path / "state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state_dir))
    project = tmp_path / "project"
    project.mkdir()
    path = project / "a.py"
    path.write_text("one\ntwo\nthree\n", encoding="utf-8")

    first = EditorApp(project, use_session=True)
    async with first.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        editor = await first.open_path(path)
        assert editor is not None
        editor.move_cursor((2, 1))
        await pilot.pause()
        first.persist_session()

    second = EditorApp(project, use_session=True)
    async with second.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert second.editor_area.tab_ids == ["file-1"]
        editor = second.editor_area.active_editor
        assert editor is not None
        assert editor.cursor_location == (2, 1)
        assert editor.has_focus
