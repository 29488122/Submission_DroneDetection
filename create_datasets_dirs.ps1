#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$datasetsRoot = Join-Path $RepoRoot "Datasets"

# Create top-level Datasets directory
if (-not (Test-Path -LiteralPath $datasetsRoot)) {
    New-Item -ItemType Directory -Path $datasetsRoot | Out-Null
    Write-Host "Created: $datasetsRoot"
} else {
    Write-Host "Already exists: $datasetsRoot"
}

$subDirs = @(
    "Al-Emadi",
    "DronePrint",
    "Augmented_Datasets_Alemadi",
    "EmoSoundscapes",
    "ESC-50-master",
    "eval_threshold",
    "H-2",
    "AuthorsCompiledSounds",
    "Svanstrom & Englund",
    "UrbanSound8K",
    "Yi et al"
)

$classSubDirs = @("yes_drone", "unknown")

$augmentedRootName = "Augmented_Datasets_Alemadi"
$augmentedVariantDirs = @(
    "Binary_Drone_Audio_AllAugments",
    "Binary_Drone_Audio_BandPassed",
    "Binary_Drone_Audio_Clipped",
    "Binary_Drone_Audio_GaussianAndBandPass",
    "Binary_Drone_Audio_GaussianNoise"
)

foreach ($name in $subDirs) {
    $fullPath = Join-Path $datasetsRoot $name
    if (-not (Test-Path -LiteralPath $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath | Out-Null
        Write-Host "Created: $fullPath"
    } else {
        Write-Host "Already exists: $fullPath"
    }

    if ($name -ne $augmentedRootName) {
        foreach ($classDir in $classSubDirs) {
            $classPath = Join-Path $fullPath $classDir
            if (-not (Test-Path -LiteralPath $classPath)) {
                New-Item -ItemType Directory -Path $classPath | Out-Null
                Write-Host "Created: $classPath"
            } else {
                Write-Host "Already exists: $classPath"
            }
        }
    }
}

$augmentedRootPath = Join-Path $datasetsRoot $augmentedRootName
foreach ($variantDir in $augmentedVariantDirs) {
    $variantPath = Join-Path $augmentedRootPath $variantDir
    if (-not (Test-Path -LiteralPath $variantPath)) {
        New-Item -ItemType Directory -Path $variantPath | Out-Null
        Write-Host "Created: $variantPath"
    } else {
        Write-Host "Already exists: $variantPath"
    }

    foreach ($classDir in $classSubDirs) {
        $classPath = Join-Path $variantPath $classDir
        if (-not (Test-Path -LiteralPath $classPath)) {
            New-Item -ItemType Directory -Path $classPath | Out-Null
            Write-Host "Created: $classPath"
        } else {
            Write-Host "Already exists: $classPath"
        }
    }
}

# Create TrainingDatasets/Al-Emadi with train/validation structure for HuggingFace audiofolder
# (CNN-LSTM and ResNet-34 expect train/ and validation/ subdirs with yes_drone/unknown inside)
$trainingDatasetsPath = Join-Path $datasetsRoot "TrainingDatasets\Al-Emadi"
foreach ($split in @("train", "validation")) {
    foreach ($cls in $classSubDirs) {
        $splitPath = Join-Path $trainingDatasetsPath "$split\$cls"
        if (-not (Test-Path -LiteralPath $splitPath)) {
            New-Item -ItemType Directory -Path $splitPath | Out-Null
            Write-Host "Created: $splitPath"
        } else {
            Write-Host "Already exists: $splitPath"
        }
    }
}

Write-Host ""
Write-Host "Done. Dataset folder structure is ready under: $datasetsRoot"