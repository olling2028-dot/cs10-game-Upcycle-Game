@echo off
setlocal
if exist "%~dp0dist\UpcycleGame.exe" (
    start "" "%~dp0dist\UpcycleGame.exe"
) else (
    python "%~dp0launch_game.pyw"
)
endlocal
