@echo off
REM ============================================================
REM Claude Code Cost Dashboard launcher
REM ============================================================
setlocal
pushd "%~dp0"

REM Pick a Python interpreter (prefer py launcher, fall back to python).
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PY=py -3"
    set "PYW=pyw -3"
) else (
    set "PY=python"
    set "PYW=pythonw"
)

REM Make sure PyQt6 is installed (one-time bootstrap).
%PY% -c "import PyQt6" 2>nul
if errorlevel 1 (
    echo Installing PyQt6 ...
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install PyQt6. Aborting.
        popd
        endlocal
        exit /b 1
    )
)

REM Make sure the Claude CLI is reachable.
where claude >nul 2>nul
if errorlevel 1 (
    echo WARNING: 'claude' was not found on PATH.
    echo Install Claude Code ^(npm i -g @anthropic-ai/claude-code^) and authenticate first.
    echo Launching the dashboard anyway so you can see the warning in the UI.
)

REM Launch detached, no console window.
start "Claude Cost Dashboard" %PYW% claude_cost_dashboard.py

popd
endlocal
