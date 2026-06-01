$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    throw "PyInstaller is not installed. Run: pip install pyinstaller"
}

Remove-Item -Recurse -Force .\build, .\dist -ErrorAction SilentlyContinue

pyinstaller --noconfirm --clean --onedir --windowed --name "UpcycleGame" `
    --add-data "images;images" `
    launch_game.pyw

$releaseDir = Join-Path $projectRoot "dist\UpcycleGame"
$zipPath = Join-Path $projectRoot "dist\UpcycleGame-Windows.zip"

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Compress-Archive -Path "$releaseDir\*" -DestinationPath $zipPath

Write-Host "Build complete."
Write-Host "Folder: $releaseDir"
Write-Host "Zip:    $zipPath"
