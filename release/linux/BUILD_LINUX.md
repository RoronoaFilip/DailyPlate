# Building Daily Plate for Linux

This folder builds Daily Plate into a folder of files with [PyInstaller](https://pyinstaller.org) and zips it.
It is the Linux counterpart of `release/windows`.

| File | Purpose |
|------|---------|
| `DailyPlate.spec` | PyInstaller recipe: folder build, bundles the seed CSV and the SVG arrows |
| `build_linux.sh` | One-command build: venv, install, tests, PyInstaller, zip |
| `BUILD_LINUX.md` | This guide |

PyInstaller does not cross-compile. Build on Linux; the release workflow does this on a GitHub runner.

## Build

You need Python 3.14, `zip`, and the Qt runtime libraries listed below. From the project folder:

```bash
bash release/linux/build_linux.sh
```

Use `--skip-tests` to skip the unit tests. The result is `release/linux/dist/DailyPlate-linux-x64.zip`
(`arm64` on ARM machines).

## Run the result

```bash
unzip DailyPlate-linux-x64.zip
./DailyPlate/DailyPlate
```

Keep the `_internal` folder next to the `DailyPlate` executable.

## Which Linux systems work

The build runs on any 64-bit Linux that has a glibc at least as new as the one it was built with.
The release workflow builds on Ubuntu 22.04 (glibc 2.35), so the zip runs on Ubuntu 22.04 or newer,
Debian 12 or newer, Fedora 36 or newer, and similar. It does not run on musl-based systems such as Alpine.

Qt needs a few system libraries. Most desktop installs already have them. If the app does not start and
mentions the Qt "xcb" platform plugin, install `libxcb-cursor0` (Debian, Ubuntu) or `xcb-util-cursor` (Fedora).

## Where the app keeps your data

1. A folder named `data` next to the `DailyPlate` executable, if it exists (portable mode).
2. Otherwise `$XDG_DATA_HOME/DailyPlate/data`, which is `~/.local/share/DailyPlate/data` by default.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `GLIBC_2.xx not found` | The system is older than the build machine. Build on that system, or use a newer one. |
| Arrows / chevrons are missing | Make sure `hiddenimports=["PySide6.QtSvg"]` is still in `DailyPlate.spec`, then rebuild. |
| Nothing happens on start | Run `./DailyPlate/DailyPlate` in a terminal and read the output. Also check `logs/application.log` in the data folder. |
| Executable is not runnable after unzip | Run `chmod +x DailyPlate/DailyPlate`. Some archive tools drop the executable bit. |
