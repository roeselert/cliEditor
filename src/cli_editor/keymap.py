"""Keymap data shared by the app and the help overlay."""

from __future__ import annotations

KEYMAP_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Files and tabs",
        [
            ("Ctrl-N", "New file"),
            ("Ctrl-O", "Open file"),
            ("Ctrl-P", "Quick open (fuzzy file finder)"),
            ("Ctrl-S", "Save"),
            ("Ctrl-Shift-S / F4", "Save As"),
            ("Ctrl-T / Alt-W", "Close current tab"),
            ("Ctrl-Tab / Ctrl-Shift-Tab", "Next / previous tab"),
            ("Ctrl-R", "Run current file"),
            ("Esc", "Stop running file"),
            ("Delete", "Delete selected file (tree focus)"),
            ("F2", "Rename selected file"),
        ],
    ),
    (
        "Editor",
        [
            ("Ctrl-C", "Copy selection"),
            ("Ctrl-V", "Paste"),
            ("Ctrl-X", "Cut"),
            ("Ctrl-A", "Select all"),
            ("Ctrl-Z", "Undo"),
            ("Ctrl-Y", "Redo"),
            ("Ctrl-F", "Find in file (tree focus: filter tree)"),
            ("Ctrl-Shift-F / F3", "Find across files"),
            ("Enter / Shift-Enter", "Next / previous match"),
            ("Ctrl-G", "Go to line"),
            ("Ctrl-Space / Alt-M", "Toggle mark mode"),
            ("Shift + arrows", "Extend selection"),
            ("Home / End", "Line start / line end"),
            ("Alt-K", "Delete to end of line"),
            ("Ctrl-W", "Toggle line wrap"),
        ],
    ),
    (
        "File tree",
        [
            ("Up / Down", "Move selection"),
            ("Right", "Open branch"),
            ("Left", "Close branch"),
            ("Enter", "Open file, or toggle directory"),
            ("Ctrl-F", "Filter files"),
            ("Home / End", "First / last item"),
        ],
    ),
    (
        "Panes and app",
        [
            ("Click", "Focus tree, tab, or editor"),
            ("Ctrl-L", "Toggle file tree"),
            ("Ctrl-K / F1", "Show this keymap"),
            ("F6 / Shift-F6", "Cycle focus"),
            ("Ctrl-Q", "Quit"),
        ],
    ),
]
