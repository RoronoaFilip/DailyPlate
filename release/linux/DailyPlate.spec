# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Daily Plate (Calorie Tracker) on Linux: folder build.
# Output: DailyPlate/ folder containing the DailyPlate executable and an _internal folder.
# Normally started by release/linux/build_linux.sh (or CI).
# Manual build:  python -m PyInstaller release/linux/DailyPlate.spec --noconfirm --clean

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent.parent   # project folder (the one containing app.py)

a = Analysis(
    [str(ROOT / "app.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        # Read-only files shipped with the app.
        (str(ROOT / "food_macros_seed.csv"), "."),
        (
            str(ROOT / "src" / "calorie_tracker" / "presentation" / "assets"),
            "calorie_tracker/presentation/assets",
        ),
    ],
    # The chevron arrows are SVGs; this makes sure Qt's SVG image/icon plugins are bundled.
    hiddenimports=["PySide6.QtSvg"],
    excludes=["tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DailyPlate",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="DailyPlate")
