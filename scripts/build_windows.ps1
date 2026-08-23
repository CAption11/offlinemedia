$ErrorActionPreference = "Stop"

Write-Host "Building OfflineMedia for Windows..."

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found on PATH."
}

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name OfflineMedia `
    --collect-all PySide6 `
    app/__main__.py

Write-Host "Build complete: dist/OfflineMedia/OfflineMedia.exe"
