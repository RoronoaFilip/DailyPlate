# Building Daily Plate as a single `.exe`

This folder contains everything needed to turn the project into one Windows executable,
`DailyPlate.exe`, using [PyInstaller](https://pyinstaller.org).

| File | Purpose |
|------|---------|
| `DailyPlate.spec` | PyInstaller recipe: one file, no console window, bundles the seed CSV and the SVG arrows |
| `build_exe.ps1` | One-command build: venv → install → tests → PyInstaller |
| `BUILD_EXE.md` | This guide |
| `app.ico` *(optional, you add it)* | Icon for the exe; picked up automatically if present |

> A Windows `.exe` can only be built **on Windows**. PyInstaller does not cross-compile.

---

## 1. Prerequisites (once)

1. **Windows 10/11, 64-bit.**
2. **Python 3.11 or newer, 64-bit**, installed from python.org with the `py` launcher.
   Use the same Python you already run the app with. If the build fails on a very new Python,
   install 3.12 or 3.13 side by side and create the venv with `py -3.12 -m venv .venv`.
3. The project folder (the one containing `app.py`) on a normal local drive. Avoid
   OneDrive-synced or network folders, which can lock files during the build.

You do **not** need to install PySide6 or PyInstaller by hand; the build script does it.

## 2. Build

From the project folder in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File release\windows\build_exe.ps1
```

The script creates `.venv` if needed, installs the project plus PyInstaller (`pip install -e ".[build]"`),
runs the unit tests, then builds. The result is:

```
release\windows\dist\DailyPlate.exe
```

Skip the tests with `-SkipTests`. Manual equivalent:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[build]"
python -m PyInstaller release\windows\DailyPlate.spec --noconfirm --clean --distpath release\windows\dist --workpath release\windows\build
```

Typical build time is 1–3 minutes. The file is tens of MB because it contains Python and Qt.
You can copy that single `.exe` anywhere; no Python needs to be installed on the target PC.

## 3. Where the exe keeps your data

The exe never writes inside itself. It picks the data folder like this:

1. **Portable mode:** if a folder named `data` sits **next to `DailyPlate.exe`**, that folder is used.
2. Otherwise: `%LOCALAPPDATA%\DailyPlate\data\` (for example `C:\Users\you\AppData\Local\DailyPlate\data\`).

It contains `calorie_tracker.sqlite3`, `logs\` and `backups\`. Settings → **Your data** shows the exact
folder and has an **Open data folder** button.

Running from source (`python app.py`) still uses `<project>\data`, as before.

### Moving your existing data into the exe

1. Close the app.
2. Copy `data\calorie_tracker.sqlite3` from the project folder to either
   `%LOCALAPPDATA%\DailyPlate\data\` (create the folders) or a `data` folder next to the exe.
3. Start `DailyPlate.exe`. Your foods, recipes and diary are there. (If the database already exists the
   built-in food seed is not re-applied.)

Alternatively use **Settings → Export backup** in the old version and **Restore backup** in the new one.

## 4. Check the result (2-minute smoke test)

Run `release\windows\dist\DailyPlate.exe` and verify:

- The window opens with no console window, and the arrows beside the date, in dropdowns and the calendar are visible
  (they are SVGs; missing arrows mean the Qt SVG plugin was not bundled, see Troubleshooting).
- Foods shows the 26 seeded foods on a first launch with no database.
- Diary → **Import CSV**: drag a `.csv` onto the window, review it, import.
- Settings → **Your data** shows the folder you expect.
- Close and reopen: your entries are still there.

## 5. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Arrows / chevrons are missing | Make sure `hiddenimports=["PySide6.QtSvg"]` is still in `DailyPlate.spec`, then rebuild with `--clean`. |
| Exe closes instantly | Set `console=True` in the spec, rebuild, run it from PowerShell and read the traceback. Also check `logs\application.log` in the data folder. |
| "Could not find the Qt platform plugin windows" | Rebuild with `--clean`; make sure `upx=False`; build on the same architecture (64-bit) you run on. |
| Antivirus / SmartScreen warns about the exe | Common for unsigned PyInstaller one-file apps. Keep UPX off, build on your own machine, and (for sharing) sign the exe with a code-signing certificate or distribute a folder build. |
| Slow first start (2–5 s) | Normal for one-file builds: they unpack to a temp folder each launch. For faster starts use a folder build (below). |
| `Failed to remove temporary directory` warnings | Harmless; occurs if the app is force-killed. |
| Build fails on a brand-new Python | Use Python 3.12/3.13 for the build venv. |

## 6. Optional extras

- **Icon:** put an `app.ico` (multi-size, 256×256 included) in this folder and rebuild.
- **Faster start (folder build):** in `DailyPlate.spec`, change the `EXE(...)` call to
  `EXE(pyz, a.scripts, [], exclude_binaries=True, name="DailyPlate", console=False, upx=False)` and append
  `coll = COLLECT(exe, a.binaries, a.datas, name="DailyPlate", upx=False)`. You then ship the whole
  `release\windows\dist\DailyPlate\` folder (zip it, or wrap it with Inno Setup).
- **Installer:** [Inno Setup](https://jrsoftware.org/isinfo.php) can wrap `DailyPlate.exe` into a Start-menu installer;
  the data folder under `%LOCALAPPDATA%` is already user-writable, so no admin rights are needed.
- **Version/updates:** bump `version` in `pyproject.toml`, rebuild, and replace the exe. The database format is unchanged
  by the exe, so existing data keeps working.

## 7. Source changes that make the exe work

These are already in the project; listed so you know what they are for:

- `src/calorie_tracker/paths.py`: finds bundled files (`sys._MEIPASS`) and chooses the writable data folder.
- `app.py`: uses those helpers and skips the `src` path hack when frozen.
- `foods_view.py` / `bootstrap.py`: use `paths.py` instead of `__file__`-relative paths.
- `pyproject.toml`: new optional dependency group `build` (PyInstaller).
