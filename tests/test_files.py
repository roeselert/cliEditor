from pathlib import Path

import pytest

from cli_editor.services.files import (
    FileError,
    find_matches,
    fuzzy_filter,
    fuzzy_score,
    iter_files,
    project_search,
    read_text,
    resolve_path,
    write_text,
)


def test_read_text_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("héllo\n", encoding="utf-8")
    assert read_text(path) == "héllo\n"


def test_read_text_rejects_missing_directory_and_binary(tmp_path: Path) -> None:
    with pytest.raises(FileError, match="does not exist"):
        read_text(tmp_path / "missing.txt")
    with pytest.raises(FileError, match="not a file"):
        read_text(tmp_path)
    binary = tmp_path / "binary.dat"
    binary.write_bytes(b"hello\x00world")
    with pytest.raises(FileError, match="binary"):
        read_text(binary)


def test_read_text_rejects_non_utf8_and_oversized(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.txt"
    invalid.write_bytes(b"\xff\xfe")
    with pytest.raises(FileError, match="UTF-8"):
        read_text(invalid)
    large = tmp_path / "large.txt"
    large.write_text("abcdef", encoding="utf-8")
    with pytest.raises(FileError, match="larger than"):
        read_text(large, max_bytes=3)


def test_write_text_does_not_create_parents_by_default(tmp_path: Path) -> None:
    target = tmp_path / "missing" / "a.txt"
    with pytest.raises(FileError, match="Cannot write"):
        write_text(target, "x")
    write_text(target, "x", create_parents=True)
    assert target.read_text(encoding="utf-8") == "x"


def test_resolve_path_relative_and_absolute(tmp_path: Path) -> None:
    assert resolve_path(tmp_path, "src/a.py") == (tmp_path / "src/a.py").resolve()
    absolute = tmp_path / "b.py"
    assert resolve_path(tmp_path, str(absolute)) == absolute.resolve()


def test_iter_files_ignores_hidden_and_noise(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("a", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.js").write_text("b", encoding="utf-8")
    (tmp_path / ".hidden.py").write_text("h", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "secret.py").write_text("s", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("x", encoding="utf-8")

    files = {path.relative_to(tmp_path).as_posix() for path in iter_files(tmp_path)}
    assert files == {"a.py", "sub/b.js"}

    hidden = {
        path.relative_to(tmp_path).as_posix()
        for path in iter_files(tmp_path, include_hidden=True)
    }
    assert ".hidden.py" in hidden
    assert ".git/secret.py" not in hidden


def test_iter_files_respects_limit(tmp_path: Path) -> None:
    for index in range(5):
        (tmp_path / f"{index}.py").write_text("x", encoding="utf-8")
    assert len(iter_files(tmp_path, max_files=2)) == 2


def test_fuzzy_filter_prefers_subsequence_matches() -> None:
    assert fuzzy_score("abc", "abc.py") is not None
    assert fuzzy_score("abc", "cba.py") is None
    assert fuzzy_filter("abc", ["cba.py", "a_b_c.py", "abc.py"]) == [
        "abc.py",
        "a_b_c.py",
    ]


def test_find_matches_is_case_insensitive_and_overlapping() -> None:
    text = "Hello hello\nHELLO\n"
    assert find_matches(text, "hello") == [(0, 0), (0, 6), (1, 0)]
    assert find_matches(text, "") == []


def test_project_search_finds_text_and_skips_binary(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("first\nneedle here\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("NEEDLE too\n", encoding="utf-8")
    (tmp_path / "binary.dat").write_bytes(b"needle\x00")
    (tmp_path / ".hidden").write_text("needle", encoding="utf-8")

    hits = project_search(tmp_path, "needle")
    assert {(hit.path.name, hit.line) for hit in hits} == {
        ("a.py", 1),
        ("b.py", 0),
    }
    assert project_search(tmp_path, "needle", max_results=1)[0].path.name == "a.py"
