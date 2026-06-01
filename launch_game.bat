@echo off
setlocal
if exist "%~dp0dist\UpcycleGame\UpcycleGame.exe" (
    start "" "%~dp0dist\UpcycleGame\UpcycleGame.exe"
) else (
    python "%~dp0launch_game.pyw"
)
endlocal
