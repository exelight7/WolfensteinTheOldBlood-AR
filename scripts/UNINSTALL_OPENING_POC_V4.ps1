# Restores the game to the exact state immediately before the Opening Runtime POC V4 test.
# Source of truth: workspace\backups\opening_runtime_v4_pretest\
# (That pretest state is Opening Runtime POC V3. For the pre-V3 state use
#  scripts\UNINSTALL_OPENING_POC_V3.ps1 instead.
#  For the pre-v1 state use scripts\UNINSTALL_OPENING_POC.ps1.
#  For full vanilla restore use the separate vanilla path:
#   python tools\install_menu_pilot.py --game "<game>" --uninstall )
param([string]$GamePath = $env:WTOB_GAME_DIR)
$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
if (-not $GamePath) { throw "Set WTOB_GAME_DIR or pass -GamePath '<game directory>'." }
$Base = Join-Path $GamePath "base"
$Pretest = Join-Path $Repo "workspace\backups\opening_runtime_v4_pretest"
$InstalledV4 = @{
    "chunk0.index"     = "85b441fdd0471f8ed8bad6c7d33d6cefc5fda15a3fd0c0e1579c920180ce22db"
    "chunk0.resources" = "da3ab200295e144db74d74bed80359802146edb99d1d4bdbaa6ef8ec9473d16e"
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
foreach ($name in $InstalledV4.Keys) {
    $liveTarget = Join-Path $Base $name
    $rollbackSource = Join-Path $Pretest $name
    if (-not (Test-Path $liveTarget)) { throw "Live file missing: $liveTarget" }
    if (-not (Test-Path $rollbackSource)) { throw "Pretest backup missing: $rollbackSource" }
    $live[$name] = Get-SHA256 $liveTarget
    $rollback[$name] = Get-SHA256 $rollbackSource
}

if ($live["chunk0.index"] -eq $rollback["chunk0.index"] -and $live["chunk0.resources"] -eq $rollback["chunk0.resources"]) {
    Write-Output "Opening POC v4 already rolled back; live state matches pretest backup. Nothing to do."
    exit 0
}

foreach ($name in $InstalledV4.Keys) {
    if ($live[$name] -ne $InstalledV4[$name]) {
        Write-Warning ("Live {0} hash does not match the installed Opening POC v4 build; restoring from pretest backup anyway." -f $name)
    }
    if ($rollback[$name] -eq $live[$name]) { Write-Output ("{0}: restore source equals live state; skipped." -f $name); continue }
    Copy-Item -LiteralPath (Join-Path $Pretest $name) -Destination (Join-Path $Base $name) -Force
    $after = Get-SHA256 (Join-Path $Base $name)
    if ($after -ne $rollback[$name]) { throw "Restore verification failed for $name" }
    Write-Output ("{0}: restored {1}" -f $name, $rollback[$name])
}
Write-Output "Opening POC v4 rollback complete (state = workspace\backups\opening_runtime_v4_pretest, i.e. Opening Runtime POC V3)."
