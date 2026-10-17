param([Parameter(Mandatory = $true)][string]$GamePath)
$ErrorActionPreference = 'Stop'
# Resolve the repository root from the scripts directory.
Push-Location (Split-Path -Path $PSScriptRoot -Parent)
try {
    python tools/install_menu_pilot.py --game $GamePath --uninstall
    if ($LASTEXITCODE -ne 0) { throw 'Arabic menu pilot restoration failed.' }
} finally { Pop-Location }
