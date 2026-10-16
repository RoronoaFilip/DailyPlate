<#
  Builds Daily Plate with PyInstaller.

  Usage (from anywhere):
    powershell -ExecutionPolicy Bypass -File release\windows\build_exe.ps1 [options]

  Options:
    --exe          Single self-contained DailyPlate.exe (default)
                   -> release\windows\dist\DailyPlate.exe
    --folder       Folder build: starts faster, fewer antivirus warnings, but you ship a whole folder
                   -> release\windows\dist\DailyPlate\DailyPlate.exe  (keep it together with the _internal folder)
    --skip-tests   Skip the unit tests before building
    --help         Show this help
  (PowerShell-style -Exe, -Folder, -SkipTests also work.)
#>
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Options)

$ErrorActionPreference = "Stop"

function Show-Usage {
    Write-Host "Usage: build_exe.ps1 [--exe | --folder] [--skip-tests] [--help]"
    Write-Host "  --exe          single DailyPlate.exe (default)  -> release\windows\dist\DailyPlate.exe"
    Write-Host "  --folder       folder build (faster start)      -> release\windows\dist\DailyPlate\DailyPlate.exe"
    Write-Host "  --skip-tests   skip the unit tests before building"
}

$mode = $null
$skipTests = $false
foreach ($option in $Options) {
    switch -Regex ($option.ToLowerInvariant()) {
        '^(--exe|-exe)$' {
            if ($mode -eq "folder") { Write-Host "Choose either --exe or --folder, not both." -ForegroundColor Red; exit 1 }
            $mode = "exe"
        }
        '^(--folder|-folder)$' {
            if ($mode -eq "exe") { Write-Host "Choose either --exe or --folder, not both." -ForegroundColor Red; exit 1 }
            $mode = "folder"
        }
        '^(--skip-tests|-skiptests)$' { $skipTests = $true }
        '^(--help|-help|-h|/\?)$' { Show-Usage; exit 0 }
        default {
            Write-Host "Unknown option: $option" -ForegroundColor Red
            Show-Usage
            exit 1
        }
    }
}
if (-not $mode) { $mode = "exe" }

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root

# --- Icon / spec sanity checks (these explain a missing exe icon) ------------------------------
$specFile = "release\windows\DailyPlate.spec"
$iconFile = "release\windows\app.ico"
if (Test-Path $iconFile) {
    Write-Host ("Icon file : {0} ({1} bytes)" -f (Resolve-Path $iconFile), (Get-Item $iconFile).Length) -ForegroundColor Cyan
} else {
    Write-Host "WARNING: $iconFile not found - the exe will get the default icon. Put app.ico in the exe folder." -ForegroundColor Yellow
}
Write-Host ("Spec file : {0} (modified {1})" -f (Resolve-Path $specFile), (Get-Item $specFile).LastWriteTime) -ForegroundColor Cyan
if (-not (Select-String -Path $specFile -Pattern "icon=" -Quiet)) {
    Write-Host "WARNING: $specFile has no icon setting - copy the newest DailyPlate.spec over it." -ForegroundColor Yellow
} elseif (-not (Select-String -Path $specFile -Pattern "Using exe icon" -Quiet)) {
    Write-Host "NOTE: $specFile is an older version (it will not print an icon message). Copy the newest one." -ForegroundColor Yellow
}

function Test-ExeIcon([string]$path) {
    # Reads the icon straight from the exe (not from Explorer's icon cache) and checks that the
    # top-centre pixel is the blue of our icon rather than the default PyInstaller icon.
    Add-Type -AssemblyName System.Drawing
    $bitmap = [System.Drawing.Icon]::ExtractAssociatedIcon((Resolve-Path $path).Path).ToBitmap()
    $pixel = $bitmap.GetPixel([int]($bitmap.Width / 2), 4)
    return ($pixel.B -gt 150 -and $pixel.B -gt ($pixel.R + 50))
}

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    py -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create .venv - is Python installed with the 'py' launcher?" }
}
& ".\.venv\Scripts\Activate.ps1"

Write-Host "Installing the app and PyInstaller..." -ForegroundColor Cyan
python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Could not upgrade pip - check your internet connection." }
python -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw "Installing the project failed - see the pip output above." }
python -m pip install "pyinstaller>=6.10"
if ($LASTEXITCODE -ne 0) { throw "Installing PyInstaller failed - see the pip output above (network/proxy?)." }
python -m PyInstaller --version
if ($LASTEXITCODE -ne 0) { throw "PyInstaller is still not available in .venv." }

if (-not $skipTests) {
    Write-Host "Running tests..." -ForegroundColor Cyan
    $env:QT_QPA_PLATFORM = "offscreen"
    python -m unittest discover
    $testExit = $LASTEXITCODE
    Remove-Item Env:\QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    if ($testExit -ne 0) { throw "Tests failed - fix them or rerun with --skip-tests." }
}

Write-Host "Building ($mode build)..." -ForegroundColor Cyan
$env:DAILYPLATE_BUILD_MODE = $mode          # read by DailyPlate.spec
try {
    python -m PyInstaller release\windows\DailyPlate.spec --noconfirm --clean `
        --distpath release\windows\dist --workpath release\windows\build
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }
}
finally {
    Remove-Item Env:\DAILYPLATE_BUILD_MODE -ErrorAction SilentlyContinue
}

$built = if ($mode -eq "folder") { "release\windows\dist\DailyPlate\DailyPlate.exe" } else { "release\windows\dist\DailyPlate.exe" }
if (Test-ExeIcon $built) {
    Write-Host "Icon check: the custom icon IS embedded in $built" -ForegroundColor Green
} else {
    Write-Host "Icon check: the custom icon is NOT embedded in $built (default icon). See the warnings above." -ForegroundColor Yellow
}

Write-Host ""
if ($mode -eq "folder") {
    Write-Host "Done: $root\release\windows\dist\DailyPlate\DailyPlate.exe" -ForegroundColor Green
    Write-Host "Ship the whole release\windows\dist\DailyPlate folder (zip it, or wrap it with Inno Setup)." -ForegroundColor Green
} else {
    Write-Host "Done: $root\release\windows\dist\DailyPlate.exe" -ForegroundColor Green
}
