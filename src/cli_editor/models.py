"""Shared data models for cliEditor."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

LANGUAGES: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
}

LANGUAGE_LABELS: dict[str | None, str] = {
    "python": "Python",
    "javascript": "JavaScript",
    "html": "HTML",
    "css": "CSS",
    None: "Plain Text",
}

IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_SEARCH_FILE_BYTES = 1 * 1024 * 1024


def language_for_path(path: Path) -> str | None:
    """Return the TextArea language name for a path, or None for plain text."""
    return LANGUAGES.get(path.suffix.lower())


@dataclass
class BufferState:
    """Metadata for one open file. The Editor widget owns the current text."""

    path: Path
    language: str | None
    saved_text: str
    cursor: tuple[int, int] = (0, 0)
    scroll: tuple[int, int] = (0, 0)
    tab_id: str = ""


@dataclass
class SessionState:
    """Serializable session data."""

    root: Path
    active: str | None = None
    tabs: list[dict] = field(default_factory=list)
    tree_visible: bool = True
    tree_width: int = 34
    version: int = 1

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "root": str(self.root),
            "active": self.active,
            "tabs": self.tabs,
            "layout": {
                "tree_visible": self.tree_visible,
                "tree_width": self.tree_width,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> SessionState:
        layout = data.get("layout") or {}
        tabs = data.get("tabs") or []
        if not isinstance(tabs, list):
            tabs = []
        try:
            tree_width = int(layout.get("tree_width", 34))
        except (TypeError, ValueError):
            tree_width = 34
        return cls(
            root=Path(data.get("root") or ".").expanduser(),
            active=data.get("active"),
            tabs=[tab for tab in tabs if isinstance(tab, dict) and tab.get("path")],
            tree_visible=bool(layout.get("tree_visible", True)),
            tree_width=tree_width,
        )
