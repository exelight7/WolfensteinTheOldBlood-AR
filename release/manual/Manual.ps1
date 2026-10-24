param([ValidateSet('Install', 'Restore')][string]$Action = 'Install', [string]$Game, [string]$Backup)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding

function Assert-Closed {
    if (Get-Process -Name 'WolfOldBlood_x64' -ErrorAction SilentlyContinue) {
        throw 'أغلق اللعبة أولًا ثم أعد المحاولة.'
    }
}
function Hash([string]$Path) {
    if (!(Test-Path -LiteralPath $Path -PathType Leaf)) { return '' }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Matches([string]$Folder, $Expected, [bool]$Flat = $false) {
    foreach ($entry in $Expected.PSObject.Properties) {
        $name = if ($Flat) { Split-Path $entry.Name -Leaf } else { $entry.Name }
        if ((Hash (Join-Path $Folder $name)) -ne $entry.Value) { return $false }
    }
    return $true
}
function Copy-Verified([string]$Source, [string]$Destination, [string]$Expected) {
    if ((Hash $Source) -ne $Expected) { throw 'تغيّر أحد الملفات أثناء العملية؛ توقف التثبيت لحماية اللعبة.' }
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    if ((Hash $Destination) -ne $Expected) { throw 'فشل التحقق من الملف المنسوخ.' }
}

try {
    Assert-Closed
    if (!$Game) { $Game = Read-Host 'أدخل مسار مجلد اللعبة' }
    $Game = (Resolve-Path -LiteralPath $Game.Trim('"')).Path
    $config = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'supported_versions.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $version = $config.supported_versions[0]
    if ((Hash (Join-Path $Game $version.executable)) -ne $version.executable_sha256) {
        throw 'نسخة اللعبة غير مدعومة، أو المجلد المختار غير صحيح.'
    }
    $files = @($version.vanilla.PSObject.Properties.Name)
    $known = (Matches $Game $version.vanilla) -or (Matches $Game $version.localized)
    foreach ($state in $version.also_accepted_states) {
        $expected = [ordered]@{}
        foreach ($name in $files) {
            if ($state.PSObject.Properties.Name -contains $name) { $expected[$name] = $state.$name }
            else { $expected[$name] = (Hash (Join-Path $Game $name)) }
        }
        $warning = Hash (Join-Path $Game 'base/graphicsdriverwarningloc.json')
        if (($warning -in @($version.vanilla.'base/graphicsdriverwarningloc.json', $version.localized.'base/graphicsdriverwarningloc.json')) -and (Matches $Game ([pscustomobject]$expected))) { $known = $true }
    }
    if (!$known) { throw 'ملفات اللعبة غير معروفة. لن نستبدلها. استعد النسخة الأصلية أو تحقّق من ملفات اللعبة عبر Steam.' }
    $workRoot = Join-Path $Game '.WolfensteinAR-manual'
    $vanilla = Join-Path $workRoot 'vanilla'
    New-Item -ItemType Directory -Path $workRoot -Force | Out-Null
    if (!(Matches $vanilla $version.vanilla $true)) {
        if ($Action -eq 'Restore') { throw 'النسخة الاحتياطية الأصلية مفقودة أو غير سليمة. استخدم التحقق من ملفات اللعبة عبر Steam.' }
        $source = $Game
        $flat = $false
        if (!(Matches $Game $version.vanilla)) {
            if (!$Backup) { $Backup = Read-Host 'أدخل مجلد النسخة الاحتياطية الأصلية الذي يحتوي على الملفات الثلاثة' }
            $source = (Resolve-Path -LiteralPath $Backup.Trim('"')).Path
            $flat = $true
            if (!(Matches $source $version.vanilla $true)) { throw 'النسخة الاحتياطية لا تحتوي على الملفات الأصلية الثلاثة الموثقة. تحقّق من اللعبة عبر Steam ثم أعد المحاولة.' }
        }
        New-Item -ItemType Directory -Path $vanilla -Force | Out-Null
        foreach ($name in $files) {
            $leaf = Split-Path $name -Leaf
            $sourceName = if ($flat) { $leaf } else { $name }
            Copy-Verified (Join-Path $source $sourceName) (Join-Path $vanilla $leaf) $version.vanilla.$name
        }
    }
    if (!(Matches $vanilla $version.vanilla $true)) { throw 'فشل التحقق من النسخة الاحتياطية الأصلية.' }
    $transaction = Join-Path $workRoot ([guid]::NewGuid().ToString('N'))
    $before = Join-Path $transaction 'before'
    $stage = Join-Path $transaction 'stage'
    New-Item -ItemType Directory -Path $before, $stage -Force | Out-Null
    $current = @{}
    foreach ($name in $files) {
        $current[$name] = Hash (Join-Path $Game $name)
        Copy-Verified (Join-Path $Game $name) (Join-Path $before (Split-Path $name -Leaf)) $current[$name]
    }
    $expectedOutput = $version.vanilla
    if ($Action -eq 'Install') {
        Write-Host 'جارٍ بناء التعريب من ملفاتك الأصلية. قد تستغرق العملية عدة دقائق...'
        & (Join-Path $PSScriptRoot 'wtob-build.exe') --game $Game --baseline $vanilla --out $stage --version $config.app_version *> (Join-Path $transaction 'build.log')
        if ($LASTEXITCODE -ne 0) { throw "تعذر بناء التعريب. راجع سجل العملية: $transaction\build.log" }
        $expectedOutput = $version.localized
        if (!(Matches $stage $expectedOutput $true)) { throw 'نتيجة بناء التعريب لا تطابق الإصدار الموثق؛ لم تتغير اللعبة.' }
    } else { $stage = $vanilla }
    Assert-Closed
    foreach ($name in $files) {
        if ((Hash (Join-Path $Game $name)) -ne $current[$name]) { throw 'تغيّرت ملفات اللعبة أثناء البناء؛ لم يبدأ الاستبدال.' }
    }
    try {
        foreach ($name in $files) { Copy-Verified (Join-Path $stage (Split-Path $name -Leaf)) (Join-Path $Game $name) $expectedOutput.$name }
        if (!(Matches $Game $expectedOutput)) { throw 'فشل التحقق النهائي.' }
    } catch {
        $failure = $_
        foreach ($name in $files) { Copy-Verified (Join-Path $before (Split-Path $name -Leaf)) (Join-Path $Game $name) $current[$name] }
        throw "فشل التثبيت واستُعيدت الملفات السابقة. $failure"
    }
    if ($Action -eq 'Install') { Write-Host 'اكتمل تثبيت التعريب بنجاح.' -ForegroundColor Green }
    else { Write-Host 'استُعيدت ملفات اللعبة الأصلية بنجاح.' -ForegroundColor Green }
    Write-Host "النسخ الاحتياطية محفوظة في: $workRoot"
    exit 0
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
