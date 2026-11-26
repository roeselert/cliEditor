# AGENTS.md

## Project

`cliEditor` is a terminal (CLI) text editor built with [Textual](https://textual.textualize.io/) (Python). The UI shows a file tree on the left and the open text file on the right. MVP scope: syntax highlighting for Python, JavaScript, HTML, and CSS.

- Treat those four languages and the two-pane layout as the MVP boundary; confirm with the user before adding other languages, panes, or major features.
- `README.md` is the user-facing keymap/feature overview; `spec.md` is the build-ready implementation spec. Keep them in sync when behavior changes.

## Stack and Textual specifics

- Use Textual's built-in widgets instead of hand-rolled equivalents: `DirectoryTree` for the left pane, `TextArea` for the editor pane.
- Syntax highlighting comes from `textual[syntax]` (pulls in tree-sitter). Set `TextArea.language`, or use `TextArea.code_editor(language=...)`; `TextArea.available_languages` lists supported names.
- `tree-sitter` is pinned to `0.25.2` in `pyproject.toml`: `0.26.x` segfaults intermittently with the JavaScript grammar.
- Dev loop: run `uv run textual run --dev cli_editor.app:EditorApp` and `uv run textual console` in a second terminal. The `textual` CLI comes from `textual-dev`, not `textual`; `--dev` live-reloads TCSS (not Python).
- Tests: pytest + pytest-asyncio with `asyncio_mode = auto`; drive the app with `async with app.run_test() as pilot`. Visual snapshots use `pytest-textual-snapshot`; only run `pytest --snapshot-update` after inspecting the generated snapshots.

## Toolchain

```bash
uv sync                                      # install app + dev tools
uv run python -m cli_editor [path]           # run the app
uv run textual run --dev cli_editor.app:EditorApp
uv run textual console                       # second terminal
uv run pytest                                # full suite
uv run pytest tests/test_app.py::test_open_save_and_dirty_tab  # single test
uv run pytest --snapshot-update              # only after reviewing snapshots
uv run ruff check .
uv run pyinstaller --clean --noconfirm packaging/clieditor.spec  # standalone binary
```

## Repo state

Implemented MVP: `src/cli_editor/` contains the app, widgets, services, TCSS, and entry point; `tests/` contains unit, Pilot UI, and snapshot tests; `pyproject.toml` + `uv.lock` define the toolchain. `README.md` is the user-facing feature/keymap overview and `spec.md` is the implementation spec. `.github/workflows/build.yml` runs lint/tests and builds the onefile binary; `packaging/` holds the PyInstaller spec and frozen entry point. No `opencode.json` yet.

## Working here

- **Wait for `GO`.** Before writing or modifying code, present a short spec: goal, files to add/change, approach, dependencies, and how you will verify it. Then stop and wait. Do not start coding until the user replies `GO` — approval of the spec alone is not permission to code.
- **Every code change ships with tests.** Add unit tests for services and `Pilot` UI tests for interactions; use snapshot tests for layout changes (see `spec.md` §10). A change is not done until `uv run pytest` passes — state any untested behavior and why.
- Use the `uv` + `src/` layout and commands above unless the user says otherwise.
