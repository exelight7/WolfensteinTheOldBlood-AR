# Restores the game to the exact state immediately before the Opening Runtime POC test.
# Source of truth: workspace\backups\opening_runtime_pretest\
# (For the state before the Subtitle POC test use scripts\UNINSTALL_SUBTITLE_POC.ps1 instead.
#  For full vanilla restore use the separate vanilla path instead:
#   python tools\install_menu_pilot.py --game "<game>" --uninstall )
param([string]$GamePath = $env:WTOB_GAME_DIR)
$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
if (-not $GamePath) { throw "Set WTOB_GAME_DIR or pass -GamePath '<game directory>'." }
$Base = Join-Path $GamePath "base"
$Pretest = Join-Path $Repo "workspace\backups\opening_runtime_pretest"
$InstalledPo = @{
    "chunk0.index"     = "595334f75932b50e9ec31260c0f6dd183486d9ad693a98ac25d08a346c713546"
    "chunk0.resources" = "8ae90ca5e02ceeec17ab27b25bf17aac65fdd691f030789ba248acd894d77a80"
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
foreach ($name in $InstalledPo.Keys) {
    $liveTarget = Join-Path $Base $name
    $rollbackSource = Join-Path $Pretest $name
    if (-not (Test-Path $liveTarget)) { throw "Live file missing: $liveTarget" }
    if (-not (Test-Path $rollbackSource)) { throw "Pretest backup missing: $rollbackSource" }
    $live[$name] = Get-SHA256 $liveTarget
    $rollback[$name] = Get-SHA256 $rollbackSource
}

if ($live["chunk0.index"] -eq $rollback["chunk0.index"] -and $live["chunk0.resources"] -eq $rollback["chunk0.resources"]) {
    Write-Output "Opening POC already rolled back; live state matches pretest backup. Nothing to do."
    exit 0
}

foreach ($name in $InstalledPo.Keys) {
    if ($live[$name] -ne $InstalledPo[$name]) {
        Write-Warning ("Live {0} hash does not match the installed Opening POC build; restoring from pretest backup anyway." -f $name)
    }
    if ($rollback[$name] -eq $live[$name]) { Write-Output ("{0}: restore source equals live state; skipped." -f $name); continue }
    Copy-Item -LiteralPath (Join-Path $Pretest $name) -Destination (Join-Path $Base $name) -Force
    $after = Get-SHA256 (Join-Path $Base $name)
    if ($after -ne $rollback[$name]) { throw "Restore verification failed for $name" }
    Write-Output ("{0}: restored {1}" -f $name, $rollback[$name])
}
Write-Output "Opening POC rollback complete (state = pretest backup, per workspace\backups\opening_runtime_pretest)."
