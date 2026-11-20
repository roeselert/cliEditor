# cliEditor

A terminal (TUI) code editor built with [Textual](https://textual.textualize.io/). The file tree sits on the left, the tabbed editor on the right, and run output below. MVP syntax highlighting: Python, JavaScript, HTML, and CSS.

> Status: MVP implemented. The app, tests, and snapshots are in this repository.

## Getting started

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
# install the app and dev tools
uv sync

# start in the current directory
uv run python -m cli_editor

# or point it at a project root
uv run python -m cli_editor /path/to/project

# the installed script also works
uv run cliEditor /path/to/project
```

Options:

- `--hidden` — show dotfiles in the file tree.
- `--no-session` — don't restore or save the previous session.

Development loop:

```bash
# run with Textual's dev tools
uv run textual run --dev cli_editor.app:EditorApp

# second terminal: inspect logs and events
uv run textual console
```

Tests and lint:

```bash
uv run pytest
uv run pytest tests/test_app.py::test_open_save_and_dirty_tab
uv run pytest --snapshot-update   # only after reviewing the generated snapshots
uv run ruff check .
```

## Layout

- **File tree** — left pane; arrow keys navigate, `Enter` opens a file or toggles a directory.
- **Editor** — right pane, one tab per open file. A `●` on the tab means unsaved changes. The editor uses the standard Textual `css` syntax theme, which is less bright than the previous VS Code Dark palette. A vertical scrollbar is always available for mouse/touch scrolling. All panes use an explicit near-black palette (`#121212`, modals `#181818`) rather than Textual theme-variable panels.
- **Output panel** — bottom pane for `Ctrl-R` run results; hidden until something runs.
- **Status bar** — path, language, dirty/mark state, run status, and cursor position.
- Click the tree, a tab, or the editor to focus that pane.
- `Ctrl-L` hides/shows the file tree. The tree width is fixed; resizing is deferred.
- If the terminal is smaller than 20×20, the app shows a "Terminal too small" message instead of a broken layout. Portrait and landscape terminals are both supported; portrait mode uses a slightly narrower tree and shorter output panel.

## Keyboard shortcuts

### Files and tabs

| Key | Action |
| --- | --- |
| `Ctrl-N` | New file |
| `Ctrl-O` | Open file by path |
| `Ctrl-P` | Quick open (fuzzy file finder) |
| `Ctrl-S` | Save |
| `Ctrl-Shift-S` / `F4` | Save As |
| `Ctrl-W` | Close current tab |
| `Ctrl-Tab` / `Ctrl-Shift-Tab` | Next / previous tab (`Alt-Right` / `Alt-Left` fallback) |
| `Ctrl-R` | Run current file |
| `Esc` | Stop a running file |
| `Delete` | Delete selected file (tree focus, with confirmation) |
| `F2` | Rename selected file (tree focus) |

### Editor

| Key | Action |
| --- | --- |
| `Ctrl-C` | Copy selection |
| `Ctrl-V` | Paste |
| `Ctrl-X` | Cut |
| `Ctrl-A` | Select all |
| `Ctrl-Z` | Undo |
| `Ctrl-Y` | Redo |
| `Ctrl-F` | Find in current file (tree focus: filter tree) |
| `Ctrl-Shift-F` / `F3` | Find across files |
| `Enter` / `Shift-Enter` | Next / previous match while find is open |
| `Ctrl-G` | Go to line |
| `Ctrl-Space` / `Alt-M` | Start/stop mark mode |
| `Shift` + arrows | Extend selection |
| `Home` / `End` | Line start / line end |
| `Alt-K` | Delete to end of line |

### File tree

| Key | Action |
| --- | --- |
| `Up` / `Down` | Move selection |
| `Right` | Expand branch |
| `Left` | Collapse branch / go to parent |
| `Enter` | Open file, or toggle directory |
| `Ctrl-F` | Filter files by name |
| `Home` / `End` | First / last item |
| `Delete` | Delete file (confirmation required) |
| `F2` | Rename file |

### Panes and app

| Key | Action |
| --- | --- |
| Click | Focus tree, tab, or editor |
| `Ctrl-L` | Toggle file tree |
| `Ctrl-K` / `F1` | Show keymap overlay |
| `F6` / `Shift-F6` | Cycle focus between panes |
| `Ctrl-Q` | Quit (prompts for unsaved changes) |

## Mark mode

`Ctrl-Space` (or `Alt-M`) starts mark mode. Arrow keys extend the selection; `Ctrl-C` copies it and exits mark mode; `Ctrl-Space` again (or `Esc`) cancels. Mark mode is for keyboard-only selection — `Shift` + arrows already works without it.

## Running files

- **Python** — runs with the interpreter that started `cliEditor`.
- **JavaScript** — runs with `node` from `PATH`; a clear error is shown if Node isn't installed.
- **HTML** — opens in the default browser.
- **CSS** — not runnable; the output panel explains why.

Output streams into the panel line by line. `Esc` stops the process (and its process group). The panel shows the command, output, and exit code.

## Unsaved changes and session

- Dirty tabs show `●`; saving clears it.
- Closing a dirty tab, quitting, or deleting a dirty file prompts **Save / Discard / Cancel**.
- On launch, restore the previous session: open tabs, active tab, cursor positions, scroll positions, and tree visibility. Unsaved buffer contents are not persisted.
- Session data lives under `platformdirs.user_state_dir("cliEditor")` (usually `~/.local/state/cliEditor/session.json` on Linux).
- The session is ignored when you open a different project root. To reset it, delete that `session.json` or launch with `--no-session`; there is no automatic reset timer.

## Key conflicts to know

- **`Ctrl-M` is `Enter`.** Terminals send the same byte (`0x0D`) for both, so mark mode uses `Ctrl-Space` instead.
- **`Ctrl-K`** normally deletes to end of line in `TextArea`; that moves to `Alt-K` so `Ctrl-K` can open the keymap.
- **`Ctrl-W`** normally deletes a word in `TextArea`; closing tabs takes it. `Ctrl-Backspace` and `Alt-Backspace` still delete a word.
- **`Ctrl-A`** normally goes to line start in `TextArea`; it now selects all. `Home` still goes to line start.
- **`Ctrl-X`** is cut, not close. Close tabs with `Ctrl-W`.
- **`Ctrl-C`** copies the editor selection; the terminal/Textual interrupt binding is not used while the editor has focus.
- **`Ctrl-Shift-S` / `Ctrl-Shift-F`** need a terminal that reports modified keys (Kitty, WezTerm, Ghostty, recent iTerm2). `F4` / `F3` are fallbacks.
- Avoid `Ctrl-I` (= `Tab`), `Ctrl-J` (= newline), and `Ctrl-H` (= Backspace); terminals cannot distinguish them from navigation keys.

## Deferred

- Draggable tree/editor divider and user-configurable pane width.
- Find options: case-sensitive, whole word, regex, and highlighting all matches.
- Draft recovery for unsaved buffers.
- Clipboard over SSH via OSC 52.
- Confirmation before running an untrusted file.
- User-configurable keybindings.
