# cliEditor

A terminal (TUI) code editor built with [Textual](https://textual.textualize.io/). The file tree sits on the left, the tabbed editor on the right, and run output below. MVP syntax highlighting: Python, JavaScript, HTML, and CSS.

> Status: early scaffold. The app is not implemented yet; this README defines the target UI and keymap.

## Layout

- **File tree** — left pane; arrow keys navigate, `Enter` opens a file or toggles a directory.
- **Editor** — right pane, one tab per open file. A `●` on the tab means unsaved changes.
- **Output panel** — bottom pane for `Ctrl-R` run results.
- Click the tree, a tab, or the editor to focus that pane; the focused pane gets an accent border.
- Drag the divider between the tree and editor to resize them.
- If the terminal is too small for both panes, show a "terminal too small" message instead of a broken layout.

## Keyboard shortcuts

### Files and tabs

| Key | Action |
| --- | --- |
| `Ctrl-N` | New file |
| `Ctrl-O` | Open file |
| `Ctrl-P` | Quick open (fuzzy file finder) |
| `Ctrl-S` | Save |
| `Ctrl-Shift-S` | Save As |
| `Ctrl-W` | Close current tab |
| `Ctrl-Tab` / `Ctrl-Shift-Tab` | Next / previous tab |
| `Ctrl-R` | Run current file |
| `Esc` | Stop a running file |
| `Delete` | Delete selected file (tree focus, with confirmation) |
| `F2` | Rename selected file |

### Editor

| Key | Action |
| --- | --- |
| `Ctrl-C` | Copy selection |
| `Ctrl-V` | Paste |
| `Ctrl-X` | Cut |
| `Ctrl-A` | Select all |
| `Ctrl-Z` | Undo |
| `Ctrl-Y` | Redo |
| `Ctrl-F` | Find in current file |
| `Ctrl-Shift-F` | Find across files |
| `Enter` / `Shift-Enter` | Next / previous match while find is open |
| `Ctrl-G` | Go to line |
| `Ctrl-Space` | Start/stop mark mode |
| `Shift` + arrows | Extend selection |
| `Home` / `End` | Line start / line end |

### File tree

| Key | Action |
| --- | --- |
| `Up` / `Down` | Move selection |
| `Right` | Expand branch |
| `Left` | Collapse branch / go to parent |
| `Enter` | Open file, or toggle directory |
| `Ctrl-F` | Filter files in the tree |
| `Home` / `End` | First / last item |
| `Delete` | Delete file (confirmation required) |
| `F2` | Rename file |

### Panes and app

| Key | Action |
| --- | --- |
| Click | Focus tree, tab, or editor |
| `Ctrl-L` | Toggle layout (show/hide file tree) |
| `Ctrl-K` | Show keymap overlay |
| `F6` / `Shift-F6` | Cycle focus between panes |
| `Ctrl-Q` | Quit |

## Mark mode

`Ctrl-Space` starts mark mode. Arrow keys extend the selection; `Ctrl-C` copies it and exits mark mode; `Ctrl-Space` again (or `Esc`) cancels. Mark mode is for keyboard-only selection — `Shift` + arrows already works without it.

## Unsaved changes and session

- Dirty tabs show `●`; saving clears it.
- Closing a dirty tab, quitting, or deleting a dirty file prompts **Save / Discard / Cancel**.
- On launch, restore the previous session: open tabs, active tab, and cursor positions.

## Key conflicts to know

- **`Ctrl-M` is `Enter`.** Terminals send the same byte (`0x0D`) for both, so mark mode uses `Ctrl-Space` instead.
- **`Ctrl-K`** normally deletes to end of line in `TextArea`; that moves to `Alt-K` so `Ctrl-K` can open the keymap.
- **`Ctrl-W`** normally deletes a word in `TextArea`; closing tabs takes it. `Ctrl-Backspace` and `Alt-Backspace` must keep deleting a word.
- **`Ctrl-A`** normally goes to line start in `TextArea`; it now selects all. `Home` still goes to line start.
- **`Ctrl-X`** is cut, not close. Close tabs with `Ctrl-W`.
- **`Ctrl-C`** copies only when there is a selection; otherwise Textual treats it as quit/interrupt.
- **`Ctrl-Shift-S` / `Ctrl-Shift-F`** need a terminal that reports modified keys (Kitty, WezTerm, Ghostty, recent iTerm2). Provide `F4` / `F3` fallbacks for terminals that don't.
- Avoid `Ctrl-I` (= `Tab`), `Ctrl-J` (= newline), and `Ctrl-H` (= Backspace); terminals cannot distinguish them from navigation keys.

## Still to decide

- What "run" means for HTML/CSS: open in a browser, lint only, or disable `Ctrl-R` for those types
- Status bar: cursor position, language, dirty indicator
- Find options: case-sensitive, whole word, regex, wrap-around
- Output panel: clear, scroll, show exit code
- Confirm before running an untrusted file
- Clipboard over SSH (OSC 52)
- User-configurable keybindings
