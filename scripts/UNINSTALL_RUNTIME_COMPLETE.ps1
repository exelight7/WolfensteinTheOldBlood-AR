# Restores the game to the exact state immediately before the runtime_complete test.
# Source of truth: workspace\backups\runtime_complete_originals\
# (That pretest state is whatever was live before install, i.e. the runtime_full corpus build.)
param([string]$GamePath = $env:WTOB_GAME_DIR)
$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
if (-not $GamePath) { throw "Set WTOB_GAME_DIR or pass -GamePath '<game directory>'." }
$Base = Join-Path $GamePath "base"
$Pretest = Join-Path $Repo "workspace\backups\runtime_complete_originals"
$Files = @("chunk0.index", "chunk0.resources")

if (Get-Process WolfOldBlood_x64 -ErrorAction SilentlyContinue) {
    throw "Close Wolfenstein: The Old Blood before restoring."
}

function Get-SHA256([string]$Path) {
    $hash = [System.Security.Cryptography.SHA256]::Create()
    $stream = [System.IO.File]::OpenRead($Path)
    try { return ([BitConverter]::ToString($hash.ComputeHash($stream)) -replace "-", "").ToLower() }
    finally { $stream.Dispose(); $hash.Dispose() }
}

$live = @{}
$rollback = @{}
foreach ($name in $Files) {
    $liveTarget = Join-Path $Base $name
    $rollbackSource = Join-Path $Pretest $name
    if (-not (Test-Path $liveTarget)) { throw "Live file missing: $liveTarget" }
    if (-not (Test-Path $rollbackSource)) { throw "Pretest backup missing: $rollbackSource" }
    $live[$name] = Get-SHA256 $liveTarget
    $rollback[$name] = Get-SHA256 $rollbackSource
}

$identical = $true
foreach ($name in $Files) { if ($live[$name] -ne $rollback[$name]) { $identical = $false } }
if ($identical) {
    Write-Output "runtime_complete patch already rolled back; live state matches pretest backup. Nothing to do."
    exit 0
}

foreach ($name in $Files) {
    if ($rollback[$name] -eq $live[$name]) { Write-Output ("{0}: restore source equals live state; skipped." -f $name); continue }
    Copy-Item -LiteralPath (Join-Path $Pretest $name) -Destination (Join-Path $Base $name) -Force
    $after = Get-SHA256 (Join-Path $Base $name)
    if ($after -ne $rollback[$name]) { throw "Restore verification failed for $name" }
    Write-Output ("{0}: restored {1}" -f $name, $rollback[$name])
}
Write-Output "runtime_complete rollback complete (state = workspace\backups\runtime_complete_originals)."
