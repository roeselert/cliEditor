# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the self-contained cliEditor binary.

Build with: uv run pyinstaller --clean --noconfirm packaging/clieditor.spec
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 - provided by PyInstaller

# Textual ships TCSS themes and loads some modules dynamically, so collect all
# of its data files and submodules rather than relying on static analysis.
datas, binaries, hiddenimports = collect_all("textual")

# The app's own stylesheet is resolved relative to the cli_editor package.
datas.append((str(ROOT / "src" / "cli_editor" / "cli_editor.tcss"), "cli_editor"))

# Textual imports grammars via importlib, which PyInstaller cannot see.
hiddenimports += [
    "tree_sitter_python",
    "tree_sitter_javascript",
    "tree_sitter_html",
    "tree_sitter_css",
]

a = Analysis(
    [str(ROOT / "packaging" / "cli_editor_entry.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="clieditor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
