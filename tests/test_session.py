import json
from pathlib import Path

from cli_editor.models import SessionState
from cli_editor.services.session import load_session, save_session


def test_session_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "state" / "session.json"
    state = SessionState(
        root=tmp_path,
        active=str(tmp_path / "a.py"),
        tabs=[{"path": str(tmp_path / "a.py"), "cursor": [2, 3]}],
        tree_visible=False,
        tree_width=42,
    )
    save_session(state, path)
    assert path.is_file()
    restored = load_session(path)
    assert restored is not None
    assert restored.root == tmp_path
    assert restored.tabs == state.tabs
    assert restored.tree_width == 42


def test_load_session_handles_missing_and_corrupt_files(tmp_path: Path) -> None:
    assert load_session(tmp_path / "missing.json") is None
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json", encoding="utf-8")
    assert load_session(corrupt) is None
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert load_session(wrong) is None


def test_load_session_ignores_bad_fields(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    path.write_text(
        json.dumps(
            {
                "root": str(tmp_path),
                "tabs": "nope",
                "layout": {"tree_width": "wide"},
            }
        ),
        encoding="utf-8",
    )
    restored = load_session(path)
    assert restored is not None
    assert restored.tabs == []
    assert restored.tree_width == 34
