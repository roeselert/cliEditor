"""Guards for the PyInstaller build inputs."""

import importlib
from pathlib import Path

from cli_editor.app import main

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_entry_point_calls_app_main() -> None:
    entry = (ROOT / "packaging" / "cli_editor_entry.py").read_text(encoding="utf-8")
    assert callable(main)
    assert "from cli_editor.app import main" in entry
    assert "main()" in entry


def test_spec_bundles_stylesheet_and_mvp_languages() -> None:
    spec = (ROOT / "packaging" / "clieditor.spec").read_text(encoding="utf-8")
    assert "cli_editor.tcss" in spec
    for language in ("python", "javascript", "html", "css"):
        assert f"tree_sitter_{language}" in spec
    # Onefile builds pass binaries and data straight to EXE; no COLLECT step.
    assert "COLLECT" not in spec


def test_mvp_grammars_are_importable() -> None:
    for language in ("python", "javascript", "html", "css"):
        module = importlib.import_module(f"tree_sitter_{language}")
        assert module.language() is not None
