"""Filesystem helpers: reading, writing, walking, and searching."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ..models import (
    IGNORE_DIRS,
    MAX_FILE_BYTES,
    MAX_SEARCH_FILE_BYTES,
)


class FileError(Exception):
    """A user-facing file error."""


def resolve_path(root: Path, raw: str) -> Path:
    """Resolve a user-supplied path against the project root."""
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def read_text(path: Path, max_bytes: int = MAX_FILE_BYTES) -> str:
    """Read a UTF-8 text file, rejecting binary and oversized files."""
    if not path.exists():
        raise FileError(f"{path} does not exist")
    if not path.is_file():
        raise FileError(f"{path} is not a file")
    try:
        size = path.stat().st_size
    except OSError as error:
        raise FileError(f"Cannot stat {path}: {error}") from error
    if size > max_bytes:
        raise FileError(f"{path.name} is larger than {max_bytes // (1024 * 1024)} MB")
    try:
        data = path.read_bytes()
    except OSError as error:
        raise FileError(f"Cannot read {path}: {error}") from error
    if b"\x00" in data[:8192]:
        raise FileError(f"{path.name} looks like a binary file")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise FileError(f"{path.name} is not valid UTF-8") from error


def write_text(path: Path, text: str, *, create_parents: bool = False) -> None:
    """Write UTF-8 text. Parent creation is opt-in for new files."""
    try:
        if create_parents:
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError as error:
        raise FileError(f"Cannot write {path}: {error}") from error


def iter_files(
    root: Path,
    *,
    include_hidden: bool = False,
    max_files: int = 10_000,
) -> list[Path]:
    """Return project files, honoring ignore rules and a result cap."""
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            directory
            for directory in dirnames
            if directory not in IGNORE_DIRS
            and (include_hidden or not directory.startswith("."))
        )
        for filename in sorted(filenames):
            if not include_hidden and filename.startswith("."):
                continue
            files.append(Path(dirpath) / filename)
            if len(files) >= max_files:
                return files
    return files


def fuzzy_score(query: str, candidate: str) -> int | None:
    """Return a simple subsequence score, or None if the query doesn't match."""
    if not query:
        return 0
    query = query.lower()
    candidate = candidate.lower()
    score = 0
    position = 0
    previous = -1
    for character in query:
        found = candidate.find(character, position)
        if found < 0:
            return None
        score += 1
        if found == previous + 1:
            score += 3
        if found == 0 or candidate[found - 1] in "/_-.":
            score += 2
        previous = found
        position = found + 1
    return score - len(candidate) // 100


def fuzzy_filter(query: str, paths: list[str], limit: int = 100) -> list[str]:
    scored: list[tuple[int, str]] = []
    for path in paths:
        score = fuzzy_score(query, path)
        if score is not None:
            scored.append((score, path))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [path for _, path in scored[:limit]]


def find_matches(text: str, query: str) -> list[tuple[int, int]]:
    """Find case-insensitive plain-text matches as (row, column) pairs."""
    if not query:
        return []
    needle = query.casefold()
    matches: list[tuple[int, int]] = []
    for row, line in enumerate(text.splitlines()):
        haystack = line.casefold()
        start = 0
        while True:
            column = haystack.find(needle, start)
            if column < 0:
                break
            matches.append((row, column))
            start = column + 1
    return matches


@dataclass
class SearchHit:
    path: Path
    line: int
    text: str


def project_search(
    root: Path,
    query: str,
    *,
    include_hidden: bool = False,
    max_results: int = 200,
) -> list[SearchHit]:
    """Search file contents under root, skipping large and binary files."""
    if not query:
        return []
    hits: list[SearchHit] = []
    needle = query.casefold()
    for path in iter_files(root, include_hidden=include_hidden):
        try:
            if path.stat().st_size > MAX_SEARCH_FILE_BYTES:
                continue
            text = read_text(path, max_bytes=MAX_SEARCH_FILE_BYTES)
        except (OSError, FileError):
            continue
        for row, line in enumerate(text.splitlines()):
            if needle in line.casefold():
                hits.append(SearchHit(path=path, line=row, text=line.strip()))
                if len(hits) >= max_results:
                    return hits
    return hits
