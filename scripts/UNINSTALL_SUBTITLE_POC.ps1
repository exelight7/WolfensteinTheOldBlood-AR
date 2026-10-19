# Restores the game to the exact state immediately before the Subtitle POC test.
# Source of truth: workspace\backups\subtitle_poc_pretest\
# (For full vanilla restore use the separate vanilla path instead:
#   python tools\install_menu_pilot.py --game "<game>" --uninstall )
param([string]$GamePath = $env:WTOB_GAME_DIR)
$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
if (-not $GamePath) { throw "Set WTOB_GAME_DIR or pass -GamePath '<game directory>'." }
$GameRoot = $GamePath
$Base = Join-Path $GameRoot "base"
$Pretest = Join-Path $Repo "workspace\backups\subtitle_poc_pretest"
$Expected = @{
    "chunk0.index"     = "7fa60970e9a173fbf6400e86f103b5876350b04b5e6a113e98cf31d87f92feba"
    "chunk0.resources" = "ed6b0ec46d11e652819d3185637568a41c18572b6045eacd61e108975869b302"
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
foreach ($name in $Expected.Keys) {
    $liveTarget = Join-Path $Base $name
    $rollbackSource = Join-Path $Pretest $name
    if (-not (Test-Path $liveTarget)) { throw "Live file missing: $liveTarget" }
    if (-not (Test-Path $rollbackSource)) { throw "Pretest backup missing: $rollbackSource" }
    $live[$name] = Get-SHA256 $liveTarget
    $rollback[$name] = Get-SHA256 $rollbackSource
}

if ($live.Values -contains $Expected[$Expected.Keys[0]] -and $live["chunk0.index"] -eq $Expected["chunk0.index"] -and $live["chunk0.resources"] -eq $Expected["chunk0.resources"]) {
    Write-Output "Subtitle POC already uninstalled; live state matches pretest expectation. Nothing to do."
    exit 0
}

foreach ($name in $Expected.Keys) {
    if ($live[$name] -ne $Expected[$name]) {
        Write-Warning ("Live {0} hash does not match the installed Subtitle POC build; restoring from pretest backup anyway." -f $name)
    }
    if ($rollback[$name] -eq $live[$name]) { Write-Output ("{0}: restore source equals live state; skipped." -f $name); continue }
    Copy-Item -LiteralPath (Join-Path $Pretest $name) -Destination (Join-Path $Base $name) -Force
    $after = Get-SHA256 (Join-Path $Base $name)
    if ($after -ne $rollback[$name]) { throw "Restore verification failed for $name" }
    Write-Output ("{0}: restored {1}" -f $name, $rollback[$name])
}
Write-Output "Subtitle POC rollback complete (state = menu pilot, per pretest backup)."
