@echo off
setlocal EnableDelayedExpansion

:: ─────────────────────────────────────────────────────────────────────────────
::  STEP 2 of 2 — Copy raw datasets into the Datasets/ structure
::
::  Prerequisites: setup_1_env.bat must have been run successfully, and all
::  manually-downloaded datasets must be placed in datasets_raw/ beforehand.
::
::  Usage:
::    setup_2_copy.bat            Copy all available datasets
::    setup_2_copy.bat --dry-run  Preview what would be copied; no changes made
::
::  Missing sources are SKIPPED with a warning (not a fatal error), so you can
::  run this script again after adding more datasets to datasets_raw/.
:: ─────────────────────────────────────────────────────────────────────────────

set "ROOT=%~dp0"
set "PS=powershell.exe -ExecutionPolicy Bypass -NoProfile"
set "DRYRUN="

if /I "%~1"=="--dry-run" set "DRYRUN=-DryRun"

echo.
echo ================================================================
echo  STEP 2 of 2  --  Copy datasets into Datasets/ structure
if defined DRYRUN echo  Mode: DRY RUN (no files will be written^)
echo ================================================================
echo.
echo  Checking what is available in datasets_raw/ ...
echo.

:: Show which raw sources are present
set "RAW=%ROOT%datasets_raw"
call :check_source "Al-Emadi"     "%RAW%\Al-Emadi_DroneAudioDataset\Binary_Drone_Audio"
call :check_source "DronePrint"   "%RAW%\DronePrint\Dataset\DS1\ExperimentallyCollected"
call :check_source "Svanstrom+E"  "%RAW%\Svanstrom_Englund\Data\Audio"
call :check_source "Authors"      "%RAW%\authorsCompiledDroneDataset"
call :check_source "ESC-50"       "%RAW%\ESC-50"
call :check_source "H-2"          "%RAW%\H-2"
call :check_source "EmoSounds"    "%RAW%\EmoSoundscapes"
call :check_source "UrbanSound8K" "%RAW%\UrbanSound8K"
call :check_source "Yi et al"     "%RAW%\Yi et al"
echo.

echo [1/1] Copying available datasets...
if defined DRYRUN (
    powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%ROOT%copy_raw_datasets.ps1" -DryRun
) else (
    powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%ROOT%copy_raw_datasets.ps1"
)
if %errorlevel% neq 0 ( echo ERROR: copy_raw_datasets.ps1 failed. & goto :fail )
echo.

echo ================================================================
echo  STEP 2 COMPLETE
echo.
echo  Any skipped datasets can be added to datasets_raw/ later
echo  and this script can be re-run safely (no duplicate copies^).
echo ================================================================
pause
exit /b 0

:check_source
set "_LABEL=%~1"
set "_PATH=%~2"
if exist "%_PATH%" (
    echo   [OK]     %_LABEL%
) else (
    echo   [ABSENT] %_LABEL%  ^(will be skipped^)
)
exit /b 0

:fail
echo.
echo ================================================================
echo  STEP 2 FAILED. See error above.
echo ================================================================
pause
exit /b 1

