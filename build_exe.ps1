$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    throw "PyInstaller is not installed. Run: pip install pyinstaller"
}

Remove-Item -Recurse -Force .\build, .\dist -ErrorAction SilentlyContinue

pyinstaller --noconfirm --clean --onefile --windowed --name "UpcycleGame" `
    --add-data "ignore\images;images" `
    launch_game.pyw

$exePath = Join-Path $projectRoot "dist\UpcycleGame.exe"

Write-Host "Build complete."
Write-Host "Exe:    $exePath"
