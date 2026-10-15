param([Parameter(Mandatory = $true)][string]$GamePath)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    python tools/install_menu_pilot.py --game $GamePath
    if ($LASTEXITCODE -ne 0) { throw 'Arabic menu pilot installation failed.' }
} finally { Pop-Location }
