#!/usr/bin/env bash
# Builds Daily Plate for Linux with PyInstaller and zips the result.
#
# Usage (from anywhere):
#   bash release/linux/build_linux.sh [--skip-tests] [--help]
#
# Output:
#   release/linux/dist/DailyPlate/                  the app folder
#   release/linux/dist/DailyPlate-linux-<arch>.zip  that folder, zipped (x64 or arm64)
#
# Set PYTHON to choose the interpreter used to create .venv (default: python3, must be 3.14).
set -euo pipefail

skip_tests=0
for option in "$@"; do
    case "$option" in
        --skip-tests) skip_tests=1 ;;
        --help|-h)
            sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unknown option: $option (try --help)" >&2
            exit 1
            ;;
    esac
done

case "$(uname -m)" in
    x86_64)          arch="x64" ;;
    aarch64|arm64)   arch="arm64" ;;
    *) echo "Unsupported CPU architecture: $(uname -m)" >&2; exit 1 ;;
esac

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"

command -v zip >/dev/null || { echo "The 'zip' command is required (e.g. sudo apt install zip)." >&2; exit 1; }

if [ ! -d .venv ]; then
    echo "Creating virtual environment..."
    "${PYTHON:-python3}" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing the app and PyInstaller..."
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install "pyinstaller>=6.10"
python -m PyInstaller --version

if [ "$skip_tests" -eq 0 ]; then
    echo "Running tests..."
    QT_QPA_PLATFORM=offscreen python -m unittest discover
fi

echo "Building..."
dist="release/linux/dist"
python -m PyInstaller release/linux/DailyPlate.spec --noconfirm --clean \
    --distpath "$dist" --workpath release/linux/build

echo "Zipping..."
zip_name="DailyPlate-linux-${arch}.zip"
rm -f "$dist/$zip_name"
# -y keeps symlinks as symlinks; zip also stores the executable bit.
(cd "$dist" && zip -q -r -y "$zip_name" DailyPlate)

echo "Done: $root/$dist/$zip_name"
