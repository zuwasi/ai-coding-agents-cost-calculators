@echo off
REM ============================================================
REM Top-level menu: pick which cost calculator to launch.
REM ============================================================
setlocal
pushd "%~dp0"

:menu
cls
echo.
echo  AI Coding Agents Cost Calculators
echo  =================================
echo.
echo   [1] Claude Code Calculator       (qt_dashboard)
echo   [2] Amp Code Calculator          (amp_dashboard)
echo   [3] Droid (Factory.ai) Calculator (droid_dashboard)
echo   [Q] Quit
echo.
set "choice="
set /p "choice=Choose: "

if /i "%choice%"=="1" (
    call "%~dp0qt_dashboard\run_dashboard.bat"
    goto :end
)
if /i "%choice%"=="2" (
    call "%~dp0amp_dashboard\run_dashboard.bat"
    goto :end
)
if /i "%choice%"=="3" (
    call "%~dp0droid_dashboard\run_dashboard.bat"
    goto :end
)
if /i "%choice%"=="Q" goto :end

echo Invalid choice.
pause >nul
goto :menu

:end
popd
endlocal
