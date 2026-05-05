@echo off
setlocal EnableDelayedExpansion

:: ─────────────────────────────────────────────────────────────────────────────
::  STEP 1 of 2 — Environment setup and auto-downloadable datasets
::
::  What this does:
::    1. Creates the Datasets/ directory structure
::    2. Creates a Python 3.11 virtual environment and installs requirements
::    3. Auto-downloads datasets available without login:
::         - Al-Emadi    (GitHub)
::         - DronePrint  (GitHub)
::         - Svanstrom and Englund (GitHub)
::         - Yi et al    (Zenodo)
::    4. Shows which datasets you must download manually before running
::       setup_2_copy.bat
::
::  Run setup_2_copy.bat after completing the manual downloads.
:: ─────────────────────────────────────────────────────────────────────────────

set "ROOT=%~dp0"
set "PS=powershell.exe -ExecutionPolicy Bypass -NoProfile"

echo.
echo ================================================================
echo  STEP 1 of 2  --  Environment + Auto-download
echo ================================================================
echo.

:: ── 1: Directory structure ───────────────────────────────────────────────────
echo [1/3] Creating Datasets/ directory structure...
%PS% -File "%ROOT%create_datasets_dirs.ps1"
if %errorlevel% neq 0 ( echo ERROR: create_datasets_dirs.ps1 failed. & goto :fail )
echo.

:: ── 2: Python env + pip ──────────────────────────────────────────────────────
echo [2/3] Setting up Python 3.11 venv and installing requirements...
%PS% -File "%ROOT%setup_datasets_and_env.ps1"
if %errorlevel% neq 0 ( echo ERROR: setup_datasets_and_env.ps1 failed. & goto :fail )
echo.

:: ── 3: Formatting hotfix (needs venv) ────────────────────────────────────────
echo [3/3] Applying datasets formatting hotfix...
%PS% -File "%ROOT%Formatting_Fix\Formatting_Fix.ps1"
if %errorlevel% neq 0 ( echo ERROR: Formatting_Fix.ps1 failed. & goto :fail )
echo.

:: ── Manual download instructions ─────────────────────────────────────────────
echo ================================================================
echo  STEP 1 COMPLETE
echo.
echo  The following datasets require a manual download.
echo  Download each one and unpack it into the folder shown.
echo.
echo  1. Authors compiled drone sounds  (Kaggle - free account required^)
echo     URL   : https://www.kaggle.com/datasets/j28l298/compiled-drone-sounds
echo     Unpack: datasets_raw\authorsCompiledDroneDataset\
echo.
echo  2. H-2 drone audio  (Mobilithek - registration required^)
echo     URL   : https://mobilithek.info/offers/605778370199691264
echo     Unpack: datasets_raw\H-2\
echo.
echo  3. ESC-50 environmental sounds  (Harvard Dataverse^)
echo     URL   : https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/YDEPUT
echo     Unpack: datasets_raw\ESC-50\
echo.
echo  4. EmoSoundscapes  (MetaCreation Lab^)
echo     URL   : https://www.metacreation.net/projects/emo-soundscapes
echo     Unpack: datasets_raw\EmoSoundscapes\
echo.
echo  5. UrbanSound8K  (free registration required^)
echo     URL   : https://urbansounddataset.weebly.com/urbansound8k.html
echo     Unpack: datasets_raw\UrbanSound8K\
echo.
echo  NOTE - H-2 dataset requires an extra conversion step after downloading.
echo  After placing H-2 XML files in datasets_raw\H-2\, run:
echo    powershell -ExecutionPolicy Bypass -File prepare_h2.ps1
echo  This converts the XML-encoded audio to WAV and applies the original
echo  file filter used in the study (files_removed_h2.csv).
echo.
echo  All paths are relative to: %ROOT%
echo ================================================================
echo.
echo  When all manual downloads are in place, run:
echo    setup_2_copy.bat
echo.
pause
exit /b 0

:fail
echo.
echo ================================================================
echo  STEP 1 FAILED. See error above.
echo ================================================================
pause
exit /b 1

