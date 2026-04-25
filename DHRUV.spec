# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path.cwd()
datas = []
memory_file = project_root / "data" / "dhruv_memory.json"
if memory_file.exists():
    datas.append((str(memory_file), "data"))
logo_file = project_root / "assets" / "dhruv-logo.png"
if logo_file.exists():
    datas.append((str(logo_file), "assets"))


a = Analysis(
    ["main.pyw"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DHRUV AI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DHRUV AI",
)
