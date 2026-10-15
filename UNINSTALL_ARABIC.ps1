param([Parameter(Mandatory = $true)][string]$GamePath)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    python tools/install_menu_pilot.py --game $GamePath --uninstall
    if ($LASTEXITCODE -ne 0) { throw 'Arabic menu pilot restoration failed.' }
} finally { Pop-Location }
