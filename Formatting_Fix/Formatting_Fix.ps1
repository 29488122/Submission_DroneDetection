#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Applying datasets formatting.py hotfix..." -ForegroundColor Cyan

# Script is expected at: submission_123\Formatting_Fix\apply_formatting_fix.ps1
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir  # submission_123

$sourceFile = Join-Path $scriptDir "formatting.py"
$targetFile = Join-Path $repoRoot ".venv311\Lib\site-packages\datasets\formatting\formatting.py"

if (-not (Test-Path $sourceFile)) {
    throw "Source file not found: $sourceFile"
}

if (-not (Test-Path $targetFile)) {
    throw "Target file not found: $targetFile`nMake sure .venv311 exists and datasets is installed."
}

# Backup existing file before overwrite
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "$targetFile.bak_$timestamp"

Copy-Item -Path $targetFile -Destination $backupFile -Force
Write-Host "Backup created: $backupFile"

# Overwrite target with fixed file
Copy-Item -Path $sourceFile -Destination $targetFile -Force
Write-Host "Patched: $targetFile" -ForegroundColor Green

# Quick verification (size/hash)
$srcHash = (Get-FileHash -Path $sourceFile -Algorithm SHA256).Hash
$dstHash = (Get-FileHash -Path $targetFile -Algorithm SHA256).Hash

if ($srcHash -ne $dstHash) {
    throw "Verification failed: target hash does not match source hash."
}

Write-Host "Verification OK (SHA256 match)." -ForegroundColor Green
Write-Host "Done."