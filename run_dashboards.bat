@echo off
REM ============================================================
REM Top-level menu: pick which cost dashboard to launch.
REM ============================================================
setlocal
pushd "%~dp0"

:menu
cls
echo.
echo  Cost Dashboards
echo  ===============
echo.
echo   [1] Claude Code Cost Dashboard   (qt_dashboard)
echo   [2] Amp Code Cost Dashboard      (amp_dashboard)
echo   [3] Droid (Factory.ai) Dashboard (droid_dashboard)
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
