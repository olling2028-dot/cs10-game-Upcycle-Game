$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    throw "PyInstaller is not installed. Run: pip install pyinstaller"
}

pyinstaller --noconfirm --clean --onefile --windowed --name "UpcycleGame" `
    --add-data "images;images" `
    launch_game.pyw

Write-Host "Build complete. Find the executable in .\dist\UpcycleGame.exe"
