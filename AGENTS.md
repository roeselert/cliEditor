# AGENTS.md

## Project

`cliEditor` is a terminal (CLI) text editor built with [Textual](https://textual.textualize.io/) (Python). The UI shows a file tree on the left and the open text file on the right. MVP scope: syntax highlighting for Python, JavaScript, HTML, and CSS.

- Treat those four languages and the two-pane layout as the MVP boundary; confirm with the user before adding other languages, panes, or major features.
- `README.md` is the user-facing keymap/feature overview; `spec.md` is the build-ready implementation spec. Keep them in sync when behavior changes.

## Stack and Textual specifics

- Use Textual's built-in widgets instead of hand-rolled equivalents: `DirectoryTree` for the left pane, `TextArea` for the editor pane.
- Syntax highlighting needs the extra: `pip install "textual[syntax]"` (pulls in tree-sitter). Set `TextArea.language`, or use `TextArea.code_editor(language=...)`; `TextArea.available_languages` lists supported names.
- Dev loop: run `textual run --dev app.py` and `textual console` in a second terminal. The `textual` CLI comes from `textual-dev`, not `textual`; `--dev` live-reloads TCSS (not Python).
- Tests: pytest + pytest-asyncio with `asyncio_mode = auto`; drive the app with `async with app.run_test() as pilot`. Visual snapshots use `pytest-textual-snapshot`; only run `pytest --snapshot-update` after inspecting the generated SVG.

## Repo state

Docs-only for now: `README.md` defines the product and keymap, and `spec.md` is the build-ready implementation spec. No source, manifest, build/test/lint config, CI, or `opencode.json` yet; history is still the single `Initial commit` on `main`.

## Working here

- **Wait for `GO`.** Before writing or modifying code, present a short spec: goal, files to add/change, approach, dependencies, and how you will verify it. Then stop and wait. Do not start coding until the user replies `GO` — approval of the spec alone is not permission to code.
- The package manager and project layout are not chosen yet; propose them in the spec before adding files.
- When a toolchain is introduced, add its exact setup/build/test commands here (including how to run a single test) and remove the placeholder notice above.
