# cliEditor — Implementation Specification

A build-ready specification for a terminal code editor. Another agent should be able to implement this document without reading the original conversation.

## 1. Goal

Build `cliEditor`, a keyboard-driven terminal (TUI) code editor with:

- A file tree on the left and a tabbed editor on the right.
- Syntax highlighting for Python, JavaScript, HTML, and CSS.
- File operations: new, open, save, save-as, rename, delete, close.
- In-file find, project-wide search, quick-open, and a keymap overlay.
- Running the current file and streaming output to a bottom panel.
- Session restore and unsaved-change protection.

## 2. Non-goals (MVP)

No LSP, autocomplete, multi-cursor, plugins, Git integration, embedded terminal, split editor panes, configurable keybindings, or remote editing. Do not add languages beyond the four listed.

## 3. Stack

- Python 3.11+
- [Textual](https://textual.textualize.io/) with the `syntax` extra: `textual[syntax]`
- `platformdirs` for the session file
- Dev: `textual-dev`, `pytest`, `pytest-asyncio`, `pytest-textual-snapshot`, `ruff`

Packaging: `uv` + `pyproject.toml` (hatchling backend), `src/` layout. Declare a console script:

```toml
[project.scripts]
cliEditor = "cli_editor.app:main"
```

Pin the Textual version actually used in `pyproject.toml`; do not rely on "latest" at build time.

## 4. Project layout

```text
pyproject.toml
README.md
spec.md
src/cli_editor/
  __init__.py
  __main__.py            # python -m cli_editor
  app.py                 # EditorApp, main(), module-level `app` for snapshots
  keymap.py              # Binding tables and help text
  models.py              # BufferState, SessionState, language detection
  services/
    files.py             # read/write/ignore rules/size checks
    runner.py            # subprocess command selection and execution
    session.py           # load/save JSON session
    search.py            # in-file and project search helpers
  widgets/
    file_tree.py         # FileTreePane + filter
    editor.py            # Editor(TextArea) with key overrides
    tabs.py              # Tabs + ContentSwitcher management
    find_bar.py          # FindBar
    output.py            # OutputPane
    status_bar.py        # StatusBar
    keymap_overlay.py    # KeymapScreen(ModalScreen)
    modals.py            # ConfirmScreen, PromptScreen
  cli_editor.tcss
tests/
  conftest.py
  test_language_detection.py
  test_files.py
  test_session.py
  test_runner.py
  test_editor_ui.py
  test_snapshots.py
```

## 5. Entry point and startup

```text
cliEditor [PATH] [--hidden] [--no-session]
```

- `PATH` is the project root; default is the current directory. Resolve to an absolute path.
- `--hidden` shows dotfiles in the tree (default: hidden).
- `--no-session` skips session restore and does not write a session on exit.
- Startup order:
  1. Parse args and build `EditorApp`.
  2. Mount layout, file tree, tabs, status bar.
  3. Restore session (unless disabled), skipping missing or unreadable files.
  4. Focus the file tree.
- Expose a module-level `app = EditorApp()` in `app.py` so `pytest-textual-snapshot` and `textual run cli_editor.app` work. `main()` calls `app.run()`.

## 6. UI

```text
┌─ cliEditor ──────────────────────────────────────────────────┐
│ ┌─ Files ─────────┐ ┌─ app.py ● │ style.css ──────────────┐  │
│ │ ▾ src           │ │  1  import sys                      │  │
│ │   ▸ app.py      │ │  2  ...                             │  │
│ │   ▸ style.css   │ │                                     │  │
│ └─────────────────┘ └─────────────────────────────────────┘  │
│ ┌─ Output ─────────────────────────────────────────────────┐  │
│ │ $ python src/app.py                                      │  │
│ │ ...                                                      │  │
│ └──────────────────────────────────────────────────────────┘  │
│ src/app.py ●   Python                        Ln 12, Col 4     │
└───────────────────────────────────────────────────────────────┘
```

### Widgets

| Area | Widget |
| --- | --- |
| Root | `EditorApp(App)` with `CSS_PATH = "cli_editor.tcss"` |
| Split | `Horizontal#main` containing tree pane and editor area |
| Tree | `FileTreePane(Container)` → optional `Input#tree-filter` + `DirectoryTree#tree` |
| Editor | `EditorArea(Container)` → `Tabs#tabs` + `ContentSwitcher#editors` |
| Output | `OutputPane(Container)` → `RichLog#output` (markup off, highlight off) |
| Find | `FindBar(Container)`, hidden by default, docked at the bottom of the editor area |
| Status | `StatusBar(Static)`, docked bottom of the screen |
| Modals | `KeymapScreen`, `ConfirmScreen`, `PromptScreen` |

Use `Tabs` + `ContentSwitcher` directly (not `TabbedContent`) so tabs can be added/removed dynamically. Each open file gets:

- A `Tab` whose `id` is `file-<n>` and label is the file name (prefix `●` when dirty).
- An `EditorPane(Container)` with the same `id`, containing one `Editor` (subclass of `TextArea`).

### Focus model

- Initial focus: file tree.
- Clicking the tree, a tab, or an editor focuses it. Clicking a tab also activates it and focuses its editor.
- `F6` / `Shift-F6` cycle tree → editor → output (output only when visible).
- Opening a file focuses the editor.
- `Editor` uses `tab_behavior="indent"`; `Tab` inserts indentation, so use `F6` for pane focus.

### Sizing and theming

- Tree default width: 30% of terminal, minimum 20 cells, maximum 50% of width. The divider is draggable.
- If terminal is smaller than 60×20, replace the layout with a centered "Terminal too small" message.
- Dark theme by default. `TextArea.code_editor(..., theme="monokai", show_line_numbers=True, soft_wrap=False)`.
- TCSS defines borders, focus accent, status bar, find bar, and modal styling.

## 7. Authoritative keymap

`Ctrl+...` means the control key. Bindings marked **priority** must be app-level `Binding(..., priority=True)` so they win over focused-widget bindings.

### Global / panes

| Key | Action | Priority |
| --- | --- | --- |
| `Ctrl-Q` | Quit (with unsaved prompt) | yes |
| `Ctrl-L` | Toggle file tree visibility | yes |
| `Ctrl-K` | Open keymap overlay | yes |
| `F6` / `Shift-F6` | Cycle focus forward/back | yes |
| `F1` | Same as `Ctrl-K` (fallback) | yes |
| Click | Focus tree/tab/editor | — |

### Files and tabs

| Key | Action | Priority |
| --- | --- | --- |
| `Ctrl-N` | New file | yes |
| `Ctrl-O` | Open file by path | yes |
| `Ctrl-P` | Quick open (fuzzy file finder) | yes |
| `Ctrl-S` | Save active file | yes |
| `Ctrl-Shift-S` | Save As (fallback `F4`) | yes |
| `Ctrl-W` | Close active tab | yes |
| `Ctrl-Tab` / `Ctrl-Shift-Tab` | Next/previous tab (fallback `Alt-Right`/`Alt-Left`) | yes |
| `Ctrl-R` | Run active file | yes |
| `Esc` | Stop running file | yes |
| `F2` | Rename selected file (tree focus) | no |
| `Delete` | Delete selected file (tree focus) | no |

### Editor

| Key | Action |
| --- | --- |
| `Ctrl-C` | Copy selection |
| `Ctrl-V` | Paste |
| `Ctrl-X` | Cut |
| `Ctrl-A` | Select all (override TextArea default) |
| `Ctrl-Z` | Undo |
| `Ctrl-Y` | Redo |
| `Ctrl-F` | Find in file (tree focus: filter tree) |
| `Ctrl-Shift-F` | Find across files (fallback `F3`) |
| `Enter` / `Shift-Enter` | Next/previous match while find bar is open |
| `Ctrl-G` | Go to line |
| `Ctrl-Space` | Toggle mark mode (fallback `Alt-M`) |
| `Shift` + arrows | Extend selection |
| `Home` / `End` | Line start / line end |
| `Alt-K` | Delete to end of line (moved off `Ctrl-K`) |
| `Ctrl-Backspace` | Delete word left (keep working after `Ctrl-W` is taken) |

### File tree

| Key | Action |
| --- | --- |
| `Up` / `Down` | Move selection |
| `Right` | Expand branch |
| `Left` | Collapse branch / go to parent |
| `Enter` | Open file, or toggle directory |
| `Ctrl-F` | Focus the tree filter |
| `Home` / `End` | First/last item |
| `Delete` | Delete file with confirmation |
| `F2` | Rename file |

### Binding implementation notes

- Set `ENABLE_COMMAND_PALETTE = False`; `Ctrl-P` is quick-open, not the palette.
- Set `ESCAPE_TO_MINIMIZE = False` on the app/screen so `Esc` is usable for find/mark/stop.
- Remove or override the app-level `Ctrl-C` "help quit" binding so it never fires while editing.
- Rebind TextArea's `ctrl+k` (delete to EOL) to `alt+k` in the `Editor` subclass.
- Override `ctrl+a` in `Editor` to call `action_select_all`; `Home` still moves to line start.
- `Ctrl-W` closes tabs globally. TextArea's word-delete remains available via `Ctrl-Backspace`.
- `Ctrl-Shift-S` and `Ctrl-Shift-F` require a terminal that reports modified keys (Kitty, WezTerm, Ghostty, recent iTerm2). Keep `F4`/`F3` fallbacks bound.
- Avoid `Ctrl-M` (= `Enter`), `Ctrl-I` (= `Tab`), `Ctrl-J` (= newline), `Ctrl-H` (= Backspace).

## 8. Feature behavior

### 8.1 File tree

- Root is the resolved `PATH`. Hidden entries are excluded unless `--hidden`.
- Ignore these directories everywhere (tree, quick open, project search): `.git`, `.hg`, `.svn`, `node_modules`, `__pycache__`, `.venv`, `venv`, `dist`, `build`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`.
- `Enter` on a directory toggles expansion; on a file opens it.
- `Ctrl-F` in the tree reveals `Input#tree-filter`, focuses it, and filters as the user types:
  - Case-insensitive substring match on the file name.
  - Show matching files plus their ancestor directories; auto-expand ancestors.
  - `Esc` clears the filter, hides the input, and returns focus to the tree.
  - Cap at 500 matches; show a "refine filter" notification if capped.
- `Delete` on a file shows a confirmation modal. On confirm, delete the file, close its tab if open, and refresh the tree. Directories are not deletable in MVP.
- `F2` on a file opens a prompt with the current name. Rename on disk; update the tab label, buffer path, and language; reject empty names, path separators, and existing targets.
- Clicking a tree item selects it; double-clicking a file opens it (optional but preferred).

### 8.2 Tabs and buffers

- One tab per open file; opening an already-open path activates the existing tab.
- Tab label: file name, prefixed with `●` when dirty.
- Closing a dirty tab prompts Save / Discard / Cancel. Cancel aborts the close.
- Closing the last tab leaves an empty editor area with a placeholder ("No file open — Ctrl-O to open").
- Switching tabs preserves cursor position, scroll position, and per-tab undo history.
- Per-file state: path, language, saved text, cursor `(row, col)`, scroll `(x, y)`.

### 8.3 File operations

- **New (`Ctrl-N`)**: prompt for a path relative to the root (or absolute). Create an empty file, open it, focus the editor. Reject existing paths.
- **Open (`Ctrl-O`)**: prompt for a path. Relative paths resolve against the root. Reject missing paths, directories, binary files, and files over 5 MB.
- **Save (`Ctrl-S`)**: write the active buffer as UTF-8. If the file no longer exists, fall back to Save As. On write error, keep the buffer dirty and show a notification.
- **Save As (`Ctrl-Shift-S`)**: prompt for a path, write, update the tab/path/language, and mark clean.
- **Quick open (`Ctrl-P`)**: walk the root once (ignore rules above), cap at 10,000 files, and show an `OptionList` with fuzzy matching on relative paths. `Enter` opens; `Esc` closes. Refresh the index when the tree changes.
- **Delete**: see 8.1. Deleting a dirty open file prompts Save / Discard / Cancel first.

### 8.4 Editing

- `Editor` is a `TextArea` subclass created with `Editor.code_editor(text=..., language=..., theme="monokai", show_line_numbers=True, soft_wrap=False, tab_behavior="indent")`.
- Language by extension:

| Extension | Language |
| --- | --- |
| `.py` | `python` |
| `.js`, `.mjs`, `.cjs` | `javascript` |
| `.html`, `.htm` | `html` |
| `.css` | `css` |
| anything else | `None` (plain text) |

- Dirty state: on every `TextArea.Changed`, compare `editor.text` with the buffer's `saved_text`. Update the tab label and status bar. Saving updates `saved_text`.
- Files are UTF-8. Reject files containing a NUL byte in the first 8 KB as binary.
- If syntax highlighting dependencies are missing, still open the file as plain text and notify once.

### 8.5 Find in file

- `Ctrl-F` (editor focus) opens `FindBar` at the bottom of the editor area and focuses its `Input`.
- Search is incremental, case-insensitive plain-text substring matching. Empty query clears highlights.
- `Enter` selects the next match; `Shift-Enter` the previous; wrap around. Show `n/total` in the bar.
- Selecting a match sets `editor.selection` to the match range and scrolls it into view.
- `Esc` closes the bar, clears the selection, and returns focus to the editor.
- No match: show `0/0` and a warning-colored border on the input.

### 8.6 Find across files

- `Ctrl-Shift-F` (fallback `F3`) opens a modal with an `Input` and a results `OptionList`.
- Plain-text, case-insensitive search under the root, honoring ignore rules and skipping files over 1 MB or containing NUL bytes.
- Results are `relative/path.py:line: text`; cap at 200 results and show a notice when capped.
- `Enter` opens the file (or activates its tab), moves the cursor to that line, and closes the modal.
- `Esc` closes the modal.

### 8.7 Mark mode

- `Ctrl-Space` (fallback `Alt-M`) toggles mark mode for the active editor.
- On enter: store the cursor as the anchor and show a `MARK` indicator in the status bar.
- In mark mode, plain arrow keys (including `Up`/`Down`/`Home`/`End`/`PageUp`/`PageDown`) extend the selection from the anchor; `Shift` + arrows behave normally.
- `Ctrl-C` copies the selection and exits mark mode.
- `Esc`, a mouse click, or `Ctrl-Space` again cancels mark mode and collapses the selection.

### 8.8 Run and output

- `Ctrl-R` runs the active file:

| Type | Command |
| --- | --- |
| `.py` | `[sys.executable, "-u", str(path)]` |
| `.js`, `.mjs`, `.cjs` | `["node", str(path)]`; notify if `node` is not on `PATH` |
| `.html`, `.htm` | `webbrowser.open(path.as_uri())` (default decision; see §13) |
| `.css` | Not runnable; show a notification |

- Run with `asyncio.create_subprocess_exec` (no shell), `cwd=path.parent`, `stdout=PIPE`, `stderr=STDOUT`, and a new process group/session so the child tree can be terminated.
- Stream decoded output line-by-line into `RichLog`. Show the exit code when it finishes.
- Only one run at a time. `Ctrl-R` while running notifies "Already running".
- `Esc` stops a run: terminate the process group, wait up to 2 seconds, then kill. Show "Stopped".
- Reveal the output pane on first run. Keep it visible until the user hides it; the pane has a clickable header to clear/collapse.
- Do not run a file with unsaved changes without saving first; `Ctrl-R` saves the active buffer automatically (or prompts on save failure).

### 8.9 Keymap overlay

- `Ctrl-K` (or `F1`) pushes `KeymapScreen`, a scrollable modal listing every binding grouped by context.
- `Esc`, `Ctrl-K`, or `F1` closes it.
- The overlay is generated from the same binding tables used by the app so it cannot drift.

### 8.10 Status bar

Show, left to right:

- Active path relative to the root, plus `●` when dirty.
- Language name (`Python`, `JavaScript`, `HTML`, `CSS`, `Plain Text`).
- `MARK` while in mark mode; run status (`RUNNING`, `EXIT 0`, `STOPPED`).
- `Ln <row+1>, Col <col+1>`.

Update on cursor/selection changes, text changes, tab activation, and run state changes.

### 8.11 Session restore

- Store JSON at `platformdirs.user_state_dir("cliEditor") / "session.json"`.
- Write atomically (temp file + `os.replace`) on quit and after tab changes (debounced ≥ 1 second).
- Schema:

```json
{
  "version": 1,
  "root": "/abs/project",
  "active": "/abs/project/src/app.py",
  "tabs": [
    {"path": "/abs/project/src/app.py", "cursor": [11, 4], "scroll": [0, 20]}
  ],
  "layout": {"tree_visible": true, "tree_width": 36}
}
```

- On load: ignore unknown fields, skip missing/unreadable files, and fall back to the current directory if `root` is missing. If the JSON is corrupt, start fresh and notify once.
- Do not persist unsaved buffer text in MVP. Document this as a crash-recovery limitation.

### 8.12 Errors and notifications

Use `App.notify` for non-blocking errors: unreadable/unwritable files, binary/large files, missing `node`, failed runs, invalid paths, and capped searches. Never crash the app on a filesystem error.

## 9. Data model

```python
@dataclass
class BufferState:
    path: Path
    language: str | None
    saved_text: str
    cursor: tuple[int, int] = (0, 0)
    scroll: tuple[int, int] = (0, 0)
    tab_id: str = ""
```

The `Editor` widget is the source of truth for current text. `BufferState.saved_text` is the clean snapshot used for dirty checks.

## 10. Testing

Commands:

```bash
uv sync --extra dev
uv run python -m cli_editor
uv run textual run --dev cli_editor.app:EditorApp
uv run textual console            # second terminal
uv run pytest
uv run pytest tests/test_editor_ui.py::test_open_and_save
uv run pytest --snapshot-update   # only after visually reviewing snapshots
uv run ruff check .
```

Required coverage:

- **Unit**: language detection, ignore rules, binary/large-file rejection, session round-trip and corrupt-session handling, run-command selection, fuzzy matcher.
- **UI (Pilot)**: open/save/save-as, dirty prompt on close/quit, tab switching, find next/prev, mark-mode copy, tree navigation and filter, keymap overlay, quick open, stop run.
- **Snapshots**: default layout, dirty tab, find bar, keymap overlay, output panel. Snapshot tests fail on first run; run `--snapshot-update` only after checking the SVGs.
- Use `app.run_test(size=(120, 40))` for UI tests and `tmp_path` for filesystem tests.

## 11. Acceptance criteria

1. `cliEditor` starts in any directory and shows a file tree plus an empty editor area.
2. Opening `.py`, `.js`, `.html`, and `.css` files shows correct highlighting and line numbers.
3. `Ctrl-S` writes changes; the dirty dot appears and clears correctly.
4. New, open, save-as, rename, and delete all work with confirmations and error handling.
5. Tabs preserve cursor, scroll, and undo history; `Ctrl-W` prompts on dirty buffers.
6. `Ctrl-F` finds and selects matches with wrap-around; `Ctrl-Shift-F` searches the project.
7. `Ctrl-P` opens files by fuzzy name; `Ctrl-K` shows the keymap.
8. `Ctrl-R` runs Python/JavaScript, streams output, and `Esc` stops it.
9. Mark mode supports keyboard-only selection and copy.
10. Tree arrows/Enter navigate and open; `Ctrl-F` filters the tree.
11. Quitting and relaunching restores tabs and cursor positions.
12. Small terminals show the "too small" message; missing syntax extras degrade to plain text.
13. `uv run pytest` passes, including Pilot and snapshot tests.

## 12. Build order

1. Scaffold `pyproject.toml`, package, entry point, TCSS, empty app shell.
2. File tree + open-file flow.
3. Tabs + `Editor` + syntax detection/highlighting.
4. Save/new/save-as/rename/delete + dirty prompts.
5. Find bar, project search, mark mode.
6. Runner + output pane.
7. Quick open, tree filter, keymap overlay.
8. Status bar, session restore, size guard.
9. Tests, snapshots, lint cleanup.

## 13. Open decisions

- HTML/CSS run behavior: this spec defaults to opening HTML in the browser and rejecting CSS. Confirm before implementation.
- Clipboard over SSH: Textual's clipboard may not reach the local machine; OSC 52 support is optional.
- User-configurable keybindings: deferred.
- Draft recovery for unsaved buffers: deferred.
- Regex/case/whole-word options for search: deferred.
