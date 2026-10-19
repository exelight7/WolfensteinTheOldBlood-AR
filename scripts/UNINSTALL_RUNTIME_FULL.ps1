# Restores the game to the exact state immediately before the full-corpus (phase 100) test.
# Source of truth: workspace\backups\runtime_full_pretest\
# (That pretest state is whatever was live before install, i.e. Opening Runtime POC V4.)
# For other rollbacks use the matching UNINSTALL_OPENING_POC_V4.ps1 / V3 / _OPENING_POC.ps1,
# or the vanilla path: python tools\install_menu_pilot.py --game "<game>" --uninstall
param([string]$GamePath = $env:WTOB_GAME_DIR)
$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
if (-not $GamePath) { throw "Set WTOB_GAME_DIR or pass -GamePath '<game directory>'." }
$Base = Join-Path $GamePath "base"
$Pretest = Join-Path $Repo "workspace\backups\runtime_full_pretest"
$Files = @("chunk0.index", "chunk0.resources", "graphicsdriverwarningloc.json")

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
    Write-Output "Full-corpus patch already rolled back; live state matches pretest backup. Nothing to do."
    exit 0
}

foreach ($name in $Files) {
    if ($rollback[$name] -eq $live[$name]) { Write-Output ("{0}: restore source equals live state; skipped." -f $name); continue }
    Copy-Item -LiteralPath (Join-Path $Pretest $name) -Destination (Join-Path $Base $name) -Force
    $after = Get-SHA256 (Join-Path $Base $name)
    if ($after -ne $rollback[$name]) { throw "Restore verification failed for $name" }
    Write-Output ("{0}: restored {1}" -f $name, $rollback[$name])
}
Write-Output "Full-corpus rollback complete (state = workspace\backups\runtime_full_pretest)."
