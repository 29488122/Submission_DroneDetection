#Requires -Version 5.1
<#
.SYNOPSIS
    Prepares the H-2 drone audio dataset for training.

.DESCRIPTION
    The H-2 dataset from mobilithek.info stores audio as base64-encoded payloads
    inside XML files.  This script runs the two-stage pipeline:

      Stage 1  xml_to_audio.py   -- Decodes each XML file and writes a .wav file.
      Stage 2  replicate_h2.py   -- Removes files listed in files_removed_h2.csv
                                    to replicate the exact file set used in the
                                    original research (excludes too-short/too-long
                                    clips that were filtered out).
      Stage 3  robocopy           -- Copies remaining WAV files into
                                    Datasets\H-2\yes_drone\

.PARAMETER H2RawDir
    Path to the folder containing the raw H-2 XML files.
    Default: <RepoRoot>\datasets_raw\H-2

.PARAMETER ConvertedDir
    Intermediate directory for decoded WAV output.
    Default: <RepoRoot>\datasets_raw\H-2_converted

.PARAMETER DryRun
    Print what would happen; do not decode, delete, or copy any files.

.EXAMPLE
    # Full run (from repo root):
    powershell -ExecutionPolicy Bypass -File .\prepare_h2.ps1

    # Preview only:
    powershell -ExecutionPolicy Bypass -File .\prepare_h2.ps1 -DryRun

    # Custom raw folder:
    powershell -ExecutionPolicy Bypass -File .\prepare_h2.ps1 -H2RawDir "D:\downloads\H-2"
#>

[CmdletBinding()]
param(
    [string]$RepoRoot,
    [string]$H2RawDir,
    [string]$ConvertedDir,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Resolve script / repo root ────────────────────────────────────────────────
if (-not $RepoRoot) {
    if ($PSScriptRoot)                         { $RepoRoot = $PSScriptRoot }
    elseif ($PSCommandPath)                    { $RepoRoot = Split-Path -Parent $PSCommandPath }
    elseif ($MyInvocation.MyCommand.Definition){ $RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition }
    else { throw "Cannot resolve repo root. Pass -RepoRoot explicitly." }
}
Set-Location -Path $RepoRoot

# ── Defaults ─────────────────────────────────────────────────────────────────
if (-not $H2RawDir)     { $H2RawDir     = Join-Path $RepoRoot "datasets_raw\H-2" }
if (-not $ConvertedDir) { $ConvertedDir = Join-Path $RepoRoot "datasets_raw\H-2_converted" }

$Python          = Join-Path $RepoRoot ".venv311\Scripts\python.exe"
$XmlToAudioPy    = Join-Path $RepoRoot "xml_to_audio.py"
$ReplicateH2Py   = Join-Path $RepoRoot "replicate_h2.py"
$FilesRemovedCsv = Join-Path $RepoRoot "files_removed_h2.csv"
$H2Target        = Join-Path $RepoRoot "Datasets\H-2\yes_drone"

# ── Preflight checks ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host "================================================================"
Write-Host " H-2 Dataset Preparation"
if ($DryRun) { Write-Host " Mode: DRY RUN (no files will be written)" }
Write-Host "================================================================"
Write-Host ""

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python venv not found: $Python`nRun setup_1_env.bat first to create the virtualenv."
}
if (-not (Test-Path -LiteralPath $H2RawDir)) {
    throw "H-2 raw directory not found: $H2RawDir`n`nDownload the H-2 dataset from:`n  https://mobilithek.info/offers/605778370199691264`nand unpack it into: $H2RawDir"
}
if (-not (Test-Path -LiteralPath $FilesRemovedCsv)) {
    throw "files_removed_h2.csv not found: $FilesRemovedCsv`nThis file should be in the repository root."
}

Write-Host "Raw XML source  : $H2RawDir"
Write-Host "Converted output: $ConvertedDir"
Write-Host "Final target    : $H2Target"
Write-Host ""

# ── Stage 1: XML -> WAV conversion ───────────────────────────────────────────
Write-Host "[1/3] Converting H-2 XML files to WAV..."
if ($DryRun) {
    $xmlCount = (Get-ChildItem -LiteralPath $H2RawDir -Filter "*.xml" -Recurse -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host "  [dry-run] Would convert $xmlCount XML file(s) to: $ConvertedDir"
} else {
    if (-not (Test-Path -LiteralPath $ConvertedDir)) {
        New-Item -ItemType Directory -Path $ConvertedDir | Out-Null
    }
    & $Python $XmlToAudioPy $H2RawDir -o $ConvertedDir --recursive
    if ($LASTEXITCODE -ne 0) { throw "xml_to_audio.py failed with exit code $LASTEXITCODE." }
    $wavCount = (Get-ChildItem -LiteralPath $ConvertedDir -Filter "*.wav" -Recurse | Measure-Object).Count
    Write-Host "  Converted. Found $wavCount WAV file(s) in: $ConvertedDir"
}
Write-Host ""

# ── Stage 2: Apply research file filter (remove out-of-range files) ───────────
Write-Host "[2/3] Applying H-2 file filter (removes recordings outside the original"
Write-Host "      duration range used in the study - see files_removed_h2.csv)..."
if ($DryRun) {
    Write-Host "  [dry-run] Would run replicate_h2.py --dry-run"
    & $Python $ReplicateH2Py $ConvertedDir $FilesRemovedCsv --dry-run
} else {
    & $Python $ReplicateH2Py $ConvertedDir $FilesRemovedCsv
    if ($LASTEXITCODE -ne 0) { throw "replicate_h2.py failed with exit code $LASTEXITCODE." }
}
Write-Host ""

# ── Stage 3: Copy to Datasets\H-2\yes_drone ──────────────────────────────────
Write-Host "[3/3] Copying filtered WAV files to Datasets\H-2\yes_drone..."
if (-not (Test-Path -LiteralPath $H2Target)) {
    New-Item -ItemType Directory -Path $H2Target | Out-Null
}

$robocopyArgs = @($ConvertedDir, $H2Target, "*.wav", "/S", "/R:2", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS", "/NP")
if ($DryRun) { $robocopyArgs += "/L" }

& robocopy @robocopyArgs | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed copying H-2 WAVs to Datasets\H-2\yes_drone." }

$finalCount = (Get-ChildItem -LiteralPath $H2Target -Filter "*.wav" -Recurse -ErrorAction SilentlyContinue | Measure-Object).Count
if ($DryRun) {
    Write-Host "  [dry-run] Preview complete."
} else {
    Write-Host "  Done. Datasets\H-2\yes_drone now contains $finalCount WAV file(s)."
}

Write-Host ""
Write-Host "================================================================"
if ($DryRun) {
    Write-Host " H-2 preparation dry-run complete. Re-run without -DryRun to apply."
} else {
    Write-Host " H-2 preparation complete."
    Write-Host " You can now run setup_2_copy.bat to copy all other datasets,"
    Write-Host " or proceed directly to training."
}
Write-Host "================================================================"

