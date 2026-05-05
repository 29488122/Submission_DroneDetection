#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$RepoRoot,
    [switch]$DryRun
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
    if ($PSScriptRoot) { $RepoRoot = $PSScriptRoot }
    elseif ($PSCommandPath) { $RepoRoot = Split-Path -Parent $PSCommandPath }
    elseif ($MyInvocation.MyCommand.Definition) { $RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition }
    else { throw "Could not determine script directory. Pass -RepoRoot explicitly." }
}
Set-Location -Path $RepoRoot
$script:SkippedSources = [System.Collections.Generic.List[string]]::new()
function Ensure-Directory {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
        Write-Host "Created: $Path"
    }
}
function Invoke-RoboCopyCopy {
    param([Parameter(Mandatory)][string]$Source,[Parameter(Mandatory)][string]$Destination,[switch]$DryRun)
    if (-not (Test-Path -LiteralPath $Source)) { Write-Warning "SKIP - source not found: $Source"; $script:SkippedSources.Add($Source); return }
    Ensure-Directory -Path $Destination
    $a = @($Source,$Destination,"/E","/R:2","/W:1","/NFL","/NDL","/NJH","/NJS","/NP"); if ($DryRun) { $a += "/L" }
    & robocopy @a | Out-Null; $rc = $LASTEXITCODE
    if ($rc -ge 8) { throw "Robocopy failed ($rc): $Source -> $Destination" }
    if ($DryRun) { Write-Host "Preview: $Source -> $Destination (robocopy code: $rc)" } else { Write-Host "Copied:  $Source -> $Destination (robocopy code: $rc)" }
}
function Invoke-RoboCopyAudioOnly {
    param([Parameter(Mandatory)][string]$Source,[Parameter(Mandatory)][string]$Destination,[switch]$DryRun)
    if (-not (Test-Path -LiteralPath $Source)) { Write-Warning "SKIP - source not found: $Source"; $script:SkippedSources.Add($Source); return }
    Ensure-Directory -Path $Destination
    $pat = @("*.wav","*.ogg","*.mp3","*.flac","*.m4a","*.aac")
    $a = @($Source,$Destination) + $pat + @("/S","/R:2","/W:1","/NFL","/NDL","/NJH","/NJS","/NP"); if ($DryRun) { $a += "/L" }
    & robocopy @a | Out-Null; $rc = $LASTEXITCODE
    if ($rc -ge 8) { throw "Robocopy failed ($rc): $Source -> $Destination" }
    if ($DryRun) { Write-Host "Preview: $Source -> $Destination (audio-only, robocopy code: $rc)" } else { Write-Host "Copied:  $Source -> $Destination (audio-only, robocopy code: $rc)" }
}
function Invoke-RoboCopyByPatterns {
    param([Parameter(Mandatory)][string]$Source,[Parameter(Mandatory)][string]$Destination,[Parameter(Mandatory)][string[]]$FilePatterns,[switch]$DryRun)
    if (-not (Test-Path -LiteralPath $Source)) { Write-Warning "SKIP - source not found: $Source"; $script:SkippedSources.Add($Source); return }
    Ensure-Directory -Path $Destination
    $a = @($Source,$Destination) + $FilePatterns + @("/R:2","/W:1","/NFL","/NDL","/NJH","/NJS","/NP"); if ($DryRun) { $a += "/L" }
    & robocopy @a | Out-Null; $rc = $LASTEXITCODE
    if ($rc -ge 8) { throw "Robocopy failed ($rc): $Source -> $Destination" }
    $pt = ($FilePatterns -join ", ")
    if ($DryRun) { Write-Host "Preview: $Source -> $Destination (patterns: $pt, robocopy code: $rc)" } else { Write-Host "Copied:  $Source -> $Destination (patterns: $pt, robocopy code: $rc)" }
}
function Copy-WithTrainValSplit {
    param([Parameter(Mandatory)][string]$SourceClassDir,[Parameter(Mandatory)][string]$TrainClassDir,[Parameter(Mandatory)][string]$ValClassDir,[double]$TrainRatio=0.8,[switch]$DryRun)
    if (-not (Test-Path -LiteralPath $SourceClassDir)) { Write-Warning "SKIP - source not found: $SourceClassDir"; $script:SkippedSources.Add($SourceClassDir); return }
    Ensure-Directory -Path $TrainClassDir; Ensure-Directory -Path $ValClassDir
    $files = Get-ChildItem -LiteralPath $SourceClassDir -File | Sort-Object Name
    $tc=[math]::Floor($files.Count*$TrainRatio); $tf=$files|Select-Object -First $tc; $vf=$files|Select-Object -Skip $tc
    $nT=($tf|Measure-Object).Count; $nV=($vf|Measure-Object).Count
    if ($DryRun) {
        Write-Host "Preview split: $SourceClassDir"
        Write-Host "  -> train ($nT files): $TrainClassDir"
        Write-Host "  -> val   ($nV files): $ValClassDir"
    } else {
        foreach ($f in $tf) { Copy-Item -LiteralPath $f.FullName -Destination $TrainClassDir -Force }
        foreach ($f in $vf) { Copy-Item -LiteralPath $f.FullName -Destination $ValClassDir   -Force }
        Write-Host "Split copied: $SourceClassDir -> train($nT) val($nV)"
    }
}
$srcAl   = Join-Path $RepoRoot "datasets_raw\Al-Emadi_DroneAudioDataset\Binary_Drone_Audio"
$dstAl   = Join-Path $RepoRoot "Datasets\Al-Emadi"
$dstTr   = Join-Path $RepoRoot "Datasets\TrainingDatasets\Al-Emadi"
$dstAug  = Join-Path $RepoRoot "Datasets\Augmented_Datasets_Alemadi"
$augVars = @("Binary_Drone_Audio_AllAugments","Binary_Drone_Audio_BandPassed","Binary_Drone_Audio_Clipped","Binary_Drone_Audio_GaussianAndBandPass","Binary_Drone_Audio_GaussianNoise")
$srcAuth = Join-Path $RepoRoot "datasets_raw\authorsCompiledDroneDataset"
$dstAuth = Join-Path $RepoRoot "Datasets\AuthorsCompiledSounds"
$srcDP   = Join-Path $RepoRoot "datasets_raw\DronePrint\Dataset\DS1\ExperimentallyCollected"
$dstDP   = Join-Path $RepoRoot "Datasets\DronePrint\yes_drone"
$srcESC  = Join-Path $RepoRoot "datasets_raw\ESC-50"
$dstESC  = Join-Path $RepoRoot "Datasets\ESC-50-master\unknown"
$srcSE   = Join-Path $RepoRoot "datasets_raw\Svanstrom_Englund\Data\Audio"
$dstSED  = Join-Path $RepoRoot "Datasets\Svanstrom & Englund\yes_drone"
$dstSEU  = Join-Path $RepoRoot "Datasets\Svanstrom & Englund\unknown"
Write-Host ""; if ($DryRun) { Write-Host "Dry-run mode." } else { Write-Host "Copy mode." }; Write-Host ""
Invoke-RoboCopyCopy -Source $srcAl -Destination $dstAl -DryRun:$DryRun
foreach ($v in $augVars) { Invoke-RoboCopyCopy -Source $srcAl -Destination (Join-Path $dstAug $v) -DryRun:$DryRun }
Invoke-RoboCopyCopy -Source $srcAuth -Destination $dstAuth -DryRun:$DryRun
Invoke-RoboCopyCopy -Source $srcDP -Destination $dstDP -DryRun:$DryRun
Invoke-RoboCopyAudioOnly -Source $srcESC -Destination $dstESC -DryRun:$DryRun
Invoke-RoboCopyByPatterns -Source $srcSE -Destination $dstSED -FilePatterns @("DRONE_*.wav") -DryRun:$DryRun
Invoke-RoboCopyByPatterns -Source $srcSE -Destination $dstSEU -FilePatterns @("HELICOPTER_*.wav","BACKGROUND_*.wav") -DryRun:$DryRun
Write-Host ""; Write-Host "Building TrainingDatasets structure (all files -> train/, validation/ left empty)..."
foreach ($cls in @("yes_drone","unknown")) {
    Copy-WithTrainValSplit -SourceClassDir (Join-Path $srcAl $cls) -TrainClassDir (Join-Path $dstTr "train\$cls") -ValClassDir (Join-Path $dstTr "validation\$cls") -TrainRatio 1.0 -DryRun:$DryRun
}
Write-Host ""; if ($DryRun) { Write-Host "Dry-run complete." } else { Write-Host "Copy complete." }
if ($script:SkippedSources.Count -gt 0) {
    Write-Host ""; Write-Host "SKIPPED sources (not in datasets_raw):" -ForegroundColor Yellow
    foreach ($s in $script:SkippedSources) { Write-Host "  - $s" -ForegroundColor Yellow }
    Write-Host "Re-run setup_2_copy.bat after adding the missing datasets." -ForegroundColor Yellow
}


