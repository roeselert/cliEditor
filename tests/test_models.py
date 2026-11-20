from pathlib import Path

from cli_editor.models import (
    BufferState,
    SessionState,
    language_for_path,
)


def test_language_for_path_maps_mvp_languages() -> None:
    assert language_for_path(Path("app.py")) == "python"
    assert language_for_path(Path("app.js")) == "javascript"
    assert language_for_path(Path("app.mjs")) == "javascript"
    assert language_for_path(Path("index.html")) == "html"
    assert language_for_path(Path("style.css")) == "css"
    assert language_for_path(Path("README.md")) is None


def test_buffer_state_defaults() -> None:
    buffer = BufferState(path=Path("a.py"), language="python", saved_text="x")
    assert buffer.cursor == (0, 0)
    assert buffer.scroll == (0, 0)
    assert buffer.tab_id == ""


def test_session_state_round_trip(tmp_path: Path) -> None:
    state = SessionState(
        root=tmp_path,
        active=str(tmp_path / "a.py"),
        tabs=[{"path": str(tmp_path / "a.py"), "cursor": [1, 2]}],
        tree_visible=False,
        tree_width=40,
    )
    restored = SessionState.from_dict(state.to_dict())
    assert restored.root == tmp_path
    assert restored.active == state.active
    assert restored.tabs == state.tabs
    assert restored.tree_visible is False
    assert restored.tree_width == 40


def test_session_state_ignores_bad_tabs() -> None:
    restored = SessionState.from_dict(
        {
            "root": ".",
            "tabs": [{"path": "ok.py"}, "bad", {"no_path": True}],
            "layout": {"tree_visible": 0, "tree_width": "bad"},
        }
    )
    assert restored.tabs == [{"path": "ok.py"}]
    assert restored.tree_visible is False
    assert restored.tree_width == 34
