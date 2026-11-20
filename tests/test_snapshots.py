import shutil
import tempfile
from pathlib import Path

from cli_editor.app import EditorApp


def snapshot_root() -> Path:
    root = Path(tempfile.gettempdir()) / "cliEditor-snapshot"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    (root / "hello.py").write_text(
        "def greet(name):\n    print(f'Hello, {name}!')\n\n\ngreet('world')\n",
        encoding="utf-8",
    )
    (root / "style.css").write_text("body { color: #eee; }\n", encoding="utf-8")
    return root


def test_default_layout(snap_compare) -> None:
    root = snapshot_root()
    app = EditorApp(root, use_session=False)

    async def before(pilot) -> None:
        await pilot.pause()
        await app.open_path(root / "hello.py")
        await pilot.pause()

    assert snap_compare(
        app,
        terminal_size=(100, 30),
        run_before=before,
    )


def test_dirty_tab(snap_compare) -> None:
    root = snapshot_root()
    app = EditorApp(root, use_session=False)

    async def before(pilot) -> None:
        await pilot.pause()
        editor = await app.open_path(root / "hello.py")
        assert editor is not None
        editor.insert("# changed\n")
        await pilot.pause()

    assert snap_compare(app, terminal_size=(100, 30), run_before=before)


def test_find_bar(snap_compare) -> None:
    root = snapshot_root()
    app = EditorApp(root, use_session=False)

    async def before(pilot) -> None:
        await pilot.pause()
        await app.open_path(root / "hello.py")
        await pilot.press("ctrl+f")
        await pilot.press("h", "e", "l", "l", "o")
        await pilot.pause()

    assert snap_compare(app, terminal_size=(100, 30), run_before=before)


def test_keymap_overlay(snap_compare) -> None:
    root = snapshot_root()
    app = EditorApp(root, use_session=False)

    async def before(pilot) -> None:
        await pilot.pause()
        await pilot.press("ctrl+k")
        await pilot.pause()

    assert snap_compare(app, terminal_size=(100, 30), run_before=before)


def test_output_panel(snap_compare) -> None:
    root = snapshot_root()
    (root / "run.py").write_text("print('SNAPSHOT OUTPUT')\n", encoding="utf-8")
    app = EditorApp(root, use_session=False)

    async def before(pilot) -> None:
        await pilot.pause()
        await app.open_path(root / "run.py")
        await pilot.press("ctrl+r")
        for _ in range(100):
            if app.run_status.startswith("EXIT"):
                break
            await pilot.pause(0.05)
        await pilot.pause()

    assert snap_compare(app, terminal_size=(100, 30), run_before=before)
