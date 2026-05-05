#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$DataRoot = Join-Path $RepoRoot "datasets_raw"
if (-not (Test-Path $DataRoot)) {
    New-Item -ItemType Directory -Path $DataRoot | Out-Null
}
$manualLinks = @(
    "Authors (Kaggle): https://www.kaggle.com/datasets/j28l298/compiled-drone-sounds",
    "H-2: https://mobilithek.info/offers/605778370199691264",
    "ESC-50: https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/YDEPUT",
    "Emo Soundscapes: https://www.metacreation.net/projects/emo-soundscapes",
    "UrbanSound8K: https://urbansounddataset.weebly.com/urbansound8k.html"
)
$manualFile = Join-Path $DataRoot "manual_download_links.txt"

function Write-Section([string]$Text) {
    Write-Host ""
    Write-Host "==== $Text ====" -ForegroundColor Cyan
}

function Ensure-Tool([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is required but not found in PATH."
    }
}

function Git-Clone-Or-Pull([string]$RepoUrl, [string]$DestDir) {
    if (Test-Path $DestDir) {
        Write-Host "Repo exists, pulling latest: $DestDir"
        Push-Location $DestDir
        try { & git pull --ff-only } finally { Pop-Location }
    } else {
        Write-Host "Cloning: $RepoUrl -> $DestDir"
        & git clone $RepoUrl $DestDir
    }
}

function Download-File([string]$Url, [string]$OutFile) {
    if (Test-Path $OutFile) {
        Write-Host "Already downloaded: $OutFile"
        return
    }
    Write-Host "Downloading $Url"
    & curl.exe -L --fail --output $OutFile $Url
}

function Ensure-Python311 {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $v = & py -3.11 --version 2>$null
        if ($LASTEXITCODE -eq 0 -and $v -match "Python 3\.11\.\d+") {
            return @{ Exe = "py"; Args = @("-3.11") }
        }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        $v = & python --version 2>$null
        if ($LASTEXITCODE -eq 0 -and $v -match "Python 3\.11\.\d+") {
            return @{ Exe = "python"; Args = @() }
        }
    }

    Write-Host ""
    Write-Host "ERROR: Python 3.11 is not installed (or not on PATH)." -ForegroundColor Red
    Write-Host "Install Python 3.11 and re-run this script."
    exit 1
}

function Get-TorchSpecFromRequirements([string]$ReqFile) {
    $content = Get-Content -Path $ReqFile -Encoding UTF8
    foreach ($line in $content) {
        $trim = $line.Trim()
        if ($trim -eq "" -or $trim.StartsWith("#")) { continue }

        if ($trim -match '^torch==([^\s#]+)$') {
            return $Matches[1]
        }
    }
    return $null
}

function Try-Install-TorchSpec([string]$PythonExe, [string]$Spec) {
    # Handles plain versions (e.g. 2.7.0) and CUDA-tagged ones (e.g. 2.7.0+cu126)
    if (-not $Spec) { return }

    Write-Host "Detected torch pin: torch==$Spec"

    if ($Spec -match '\+cu(\d+)$') {
        $cuTag = $Matches[1]  # e.g. 126
        $idx = "https://download.pytorch.org/whl/cu$cuTag"
        Write-Host "Attempting CUDA wheel install from: $idx"

        & $PythonExe -m pip install "torch==$Spec" --index-url $idx
        if ($LASTEXITCODE -ne 0) {
            Write-Host "CUDA-tagged torch install failed for torch==$Spec at $idx" -ForegroundColor Yellow
            Write-Host "Falling back to base torch version from PyPI..." -ForegroundColor Yellow

            $base = $Spec.Split("+")[0]
            & $PythonExe -m pip install "torch==$base"
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to install torch==$Spec and fallback torch==$base"
            }
        }
    } else {
        & $PythonExe -m pip install "torch==$Spec"
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install torch==$Spec"
        }
    }
}

function Install-Requirements-Safely([string]$PythonExe, [string]$ReqFile) {
    # First try normal install
    Write-Host "Installing from: $ReqFile"
    & $PythonExe -m pip install -r $ReqFile
    if ($LASTEXITCODE -eq 0) { return }

    # If failed, try torch-aware fallback path
    Write-Host "Initial install failed for $ReqFile. Trying torch-aware fallback..." -ForegroundColor Yellow

    $torchSpec = Get-TorchSpecFromRequirements $ReqFile
    if (-not $torchSpec) {
        throw "Install failed for $ReqFile and no torch pin found for fallback."
    }

    Try-Install-TorchSpec $PythonExe $torchSpec

    # Re-run requirements without dependencies to avoid torch resolver conflict.
    & $PythonExe -m pip install -r $ReqFile --no-deps
    if ($LASTEXITCODE -ne 0) {
        throw "Fallback install with --no-deps failed for $ReqFile"
    }

    # Install missing deps normally (best effort)
    & $PythonExe -m pip check
    if ($LASTEXITCODE -ne 0) {
        Write-Host "pip check reported dependency issues. You may need manual adjustment." -ForegroundColor Yellow
    }
}

function Install-AllRequirements([string]$PythonExe) {
    $reqFiles = Get-ChildItem -Path $RepoRoot -Recurse -Filter "requirements.txt" | Select-Object -ExpandProperty FullName
    if (-not $reqFiles) {
        Write-Host "No requirements.txt files found."
        return
    }

    foreach ($req in $reqFiles) {
        Install-Requirements-Safely $PythonExe $req
    }
}

Write-Section "Preflight"
Ensure-Tool "git"
Ensure-Tool "curl.exe"
$pyInfo = Ensure-Python311
Write-Host "Python 3.11 detected via: $($pyInfo.Exe) $($pyInfo.Args -join ' ')"

Write-Section "Auto-download / clone datasets"

# GitHub datasets
Git-Clone-Or-Pull "https://github.com/saraalemadi/DroneAudioDataset/" (Join-Path $DataRoot "Al-Emadi_DroneAudioDataset")
Git-Clone-Or-Pull "https://github.com/DronePrint/DronePrint" (Join-Path $DataRoot "DronePrint")
Git-Clone-Or-Pull "https://github.com/DroneDetectionThesis/Drone-detection-dataset" (Join-Path $DataRoot "Svanstrom_Englund")

# Yi et al direct archive
$yiZip = Join-Path $DataRoot "Yi_zenodo_7779574_files.zip"
Download-File "https://zenodo.org/api/records/7779574/files-archive" $yiZip

Write-Section "Manual-download datasets"
$manualLinks = @(
    "Authors (Kaggle): https://www.kaggle.com/datasets/j28l298/compiled-drone-sounds",
    "H-2: https://mobilithek.info/offers/605778370199691264",
    "ESC-50: https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/YDEPUT",
    "Emo Soundscapes: https://www.metacreation.net/projects/emo-soundscapes",
    "UrbanSound8K: https://urbansounddataset.weebly.com/urbansound8k.html"
)

$manualFile = Join-Path $DataRoot "manual_download_links.txt"
$manualLinks | Set-Content -Path $manualFile -Encoding UTF8

Write-Host "Please download these manually:"
$manualLinks | ForEach-Object { Write-Host " - $_" }
Write-Host "Saved manual links to: $manualFile"

Write-Section "Create + activate Python 3.11 venv"
$venvDir = Join-Path $RepoRoot ".venv311"
if (-not (Test-Path $venvDir)) {
    & $pyInfo.Exe @($pyInfo.Args + @("-m", "venv", $venvDir))
    Write-Host "Created venv at: $venvDir"
} else {
    Write-Host "Venv already exists: $venvDir"
}

. (Join-Path $venvDir "Scripts\Activate.ps1")
Write-Host "Activated: $venvDir"

Write-Section "Install requirements"
python -m pip install --upgrade pip setuptools wheel
Install-AllRequirements "python"

Write-Section "Done"
Write-Host "Setup complete."
Write-Host "Later activation command:"
Write-Host "  . .\.venv311\Scripts\Activate.ps1"

Write-Host ""
Write-Host "Manual dataset downloads still required:" -ForegroundColor Yellow
$manualLinks | ForEach-Object { Write-Host " - $_" }
Write-Host "Saved manual links to: $manualFile"