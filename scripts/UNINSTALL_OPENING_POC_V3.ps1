# Restores the game to the exact state immediately before the Opening Runtime POC V3 test.
# Source of truth: workspace\backups\opening_runtime_v3_pretest\
# (That pretest state is Opening Runtime POC v1. For the pre-v1 state use
#  scripts\UNINSTALL_OPENING_POC.ps1 instead.
#  For full vanilla restore use the separate vanilla path:
#   python tools\install_menu_pilot.py --game "<game>" --uninstall )
param([string]$GamePath = $env:WTOB_GAME_DIR)
$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
if (-not $GamePath) { throw "Set WTOB_GAME_DIR or pass -GamePath '<game directory>'." }
$Base = Join-Path $GamePath "base"
$Pretest = Join-Path $Repo "workspace\backups\opening_runtime_v3_pretest"
$InstalledV3 = @{
    "chunk0.index"     = "595334f75932b50e9ec31260c0f6dd183486d9ad693a98ac25d08a346c713546"
    "chunk0.resources" = "79c09ba561062bf39df3696b7ab75d2518cd591b8f8b4cbc9affc76e35cfe4c9"
}

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
foreach ($name in $InstalledV3.Keys) {
    $liveTarget = Join-Path $Base $name
    $rollbackSource = Join-Path $Pretest $name
    if (-not (Test-Path $liveTarget)) { throw "Live file missing: $liveTarget" }
    if (-not (Test-Path $rollbackSource)) { throw "Pretest backup missing: $rollbackSource" }
    $live[$name] = Get-SHA256 $liveTarget
    $rollback[$name] = Get-SHA256 $rollbackSource
}

if ($live["chunk0.index"] -eq $rollback["chunk0.index"] -and $live["chunk0.resources"] -eq $rollback["chunk0.resources"]) {
    Write-Output "Opening POC v3 already rolled back; live state matches pretest backup. Nothing to do."
    exit 0
}

foreach ($name in $InstalledV3.Keys) {
    if ($live[$name] -ne $InstalledV3[$name]) {
        Write-Warning ("Live {0} hash does not match the installed Opening POC v3 build; restoring from pretest backup anyway." -f $name)
    }
    if ($rollback[$name] -eq $live[$name]) { Write-Output ("{0}: restore source equals live state; skipped." -f $name); continue }
    Copy-Item -LiteralPath (Join-Path $Pretest $name) -Destination (Join-Path $Base $name) -Force
    $after = Get-SHA256 (Join-Path $Base $name)
    if ($after -ne $rollback[$name]) { throw "Restore verification failed for $name" }
    Write-Output ("{0}: restored {1}" -f $name, $rollback[$name])
}
Write-Output "Opening POC v3 rollback complete (state = workspace\backups\opening_runtime_v3_pretest, i.e. Opening Runtime POC v1)."
