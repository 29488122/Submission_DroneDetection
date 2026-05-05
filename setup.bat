@echo off
setlocal EnableDelayedExpansion

:: ─────────────────────────────────────────────────────────────────────────────
::  Replication — top-level setup entry point
::
::  The setup is split into two steps because some datasets require a manual
::  download (registration / license agreement) before data can be copied.
::
::  STEP 1 — setup_1_env.bat
::    Creates directory structure, builds Python 3.11 venv, installs packages,
::    auto-downloads datasets that are freely accessible (GitHub / Zenodo),
::    and shows instructions for the remaining manual downloads.
::
::  STEP 2 — setup_2_copy.bat
::    Copies all available raw datasets into the Datasets/ structure.
::    Any source that is still absent is skipped with a warning so you can
::    re-run safely after adding more datasets later.
::
::  Usage:
::    setup.bat              Print this help and run step 1
::    setup.bat --step1      Run step 1 only
::    setup.bat --step2      Run step 2 only
::    setup.bat --step2 --dry-run   Preview step 2 without copying files
::    setup.bat --all        Run step 1 then step 2 (unattended, no manual pause)
:: ─────────────────────────────────────────────────────────────────────────────

set "ROOT=%~dp0"
set "MODE=help"
set "DRYRUN="

if /I "%~1"=="--step1"   set "MODE=step1"
if /I "%~1"=="--step2"   set "MODE=step2"
if /I "%~1"=="--all"     set "MODE=all"
if /I "%~2"=="--dry-run" set "DRYRUN=--dry-run"

if "%MODE%"=="step1" goto :do_step1
if "%MODE%"=="step2" goto :do_step2
if "%MODE%"=="all"   goto :do_all

:: ── Default: show instructions then run step 1 ───────────────────────────────
echo.
echo ================================================================
echo  Replication Setup
echo ================================================================
echo.
echo  This setup runs in TWO steps:
echo.
echo  STEP 1  setup_1_env.bat
echo    - Creates Datasets/ folder structure
echo    - Builds Python 3.11 venv and installs all requirements
echo    - Auto-downloads: Al-Emadi, DronePrint, Svanstrom+Englund, Yi et al
echo    - Shows instructions for 5 datasets that require manual download
echo.
echo  (Manual downloads required between steps)
echo.
echo  STEP 2  setup_2_copy.bat
echo    - Checks which raw sources are present in datasets_raw/
echo    - Copies each available dataset into the correct Datasets/ subfolder
echo    - Skips missing datasets with a warning - safe to re-run later
echo.
echo ================================================================
echo  Starting STEP 1 now...
echo ================================================================
echo.
pause

:do_step1
call "%ROOT%setup_1_env.bat"
if %errorlevel% neq 0 goto :fail
exit /b 0

:do_step2
if defined DRYRUN (
    call "%ROOT%setup_2_copy.bat" --dry-run
) else (
    call "%ROOT%setup_2_copy.bat"
)
if %errorlevel% neq 0 goto :fail
exit /b 0

:do_all
echo Running step 1 (environment + auto-downloads^)...
call "%ROOT%setup_1_env.bat"
if %errorlevel% neq 0 goto :fail
echo.
echo Running step 2 (copy datasets^)...
if defined DRYRUN (
    call "%ROOT%setup_2_copy.bat" --dry-run
) else (
    call "%ROOT%setup_2_copy.bat"
)
if %errorlevel% neq 0 goto :fail
exit /b 0

:fail
echo.
echo ================================================================
echo  Setup FAILED. See error above.
echo ================================================================
pause
exit /b 1
