param([switch]$Kiszolgalo, [switch]$ElsoAdmin, [switch]$Ellenorzes, [switch]$Telepites, [string]$PythonExe)
$ErrorActionPreference = 'Stop'
$projektMappa = Split-Path -Parent $PSScriptRoot
$pythonMappa = Join-Path $projektMappa 'python'
$kornyezetPython = Join-Path $projektMappa '.venv\Scripts\python.exe'

$jeloltek = [System.Collections.Generic.List[string]]::new()
if (-not $Telepites -and (Test-Path -LiteralPath $kornyezetPython)) {
    $jeloltek.Add($kornyezetPython)
}
if ($PythonExe) {
    $jeloltek.Add($PythonExe)
} else {
    $pyIndito = Get-Command py -ErrorAction SilentlyContinue
    if ($pyIndito) {
        foreach ($sor in (& $pyIndito.Source -0p 2>$null)) {
            if ($sor -match '([A-Za-z]:\\.*?python\.exe)\s*$') {
                $jeloltek.Add($Matches[1].Trim())
            }
        }
        $utvonal = & $pyIndito.Source -3 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $utvonal) { $jeloltek.Add($utvonal.Trim()) }
    }


    foreach ($parancsNev in @('python3.14','python3.13','python3.12','python3.11','python')) {
        $parancs = Get-Command $parancsNev -ErrorAction SilentlyContinue
        if ($parancs) {
    		$jeloltek.Add($parancs.Source)
	}
    }

    foreach ($gyoker in @(
        'HKCU:\Software\Python\PythonCore',
        'HKLM:\Software\Python\PythonCore',
        'HKLM:\Software\WOW6432Node\Python\PythonCore'
    )) {
        foreach ($verzioKulcs in (Get-ChildItem -LiteralPath $gyoker -ErrorAction SilentlyContinue)) {
            $telepitesiKulcs = Get-Item -LiteralPath (Join-Path $verzioKulcs.PSPath 'InstallPath') -ErrorAction SilentlyContinue
            if ($telepitesiKulcs) {
                $telepitesiUt = $telepitesiKulcs.GetValue('')
                if ($telepitesiUt) { $jeloltek.Add((Join-Path $telepitesiUt 'python.exe')) }
                $exeUt = $telepitesiKulcs.GetValue('ExecutablePath')
                if ($exeUt) { $jeloltek.Add($exeUt) }
            }
        }
    }

    foreach ($gyoker in @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python'),
        $env:ProgramFiles,
        ${env:ProgramFiles(x86)}
    )) {
        if ($gyoker -and (Test-Path -LiteralPath $gyoker)) {
            foreach ($mappa in (Get-ChildItem -LiteralPath $gyoker -Directory -Filter 'Python*' -ErrorAction SilentlyContinue)) {
                $jeloltek.Add((Join-Path $mappa.FullName 'python.exe'))
            }
        }
    }
}

$latottak = @{}
$kivalasztottPython = $null
foreach ($jelolt in $jeloltek) {
    if (-not $jelolt -or -not (Test-Path -LiteralPath $jelolt)) { continue }
    $teljesUt = (Resolve-Path -LiteralPath $jelolt).Path
    if ($latottak.ContainsKey($teljesUt)) { continue }
    $latottak[$teljesUt] = $true
    try {
        & $teljesUt -I -c "import sys,struct; sys.exit(0 if sys.version_info >= (3,11) and struct.calcsize('P') == 8 else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $kivalasztottPython = $teljesUt
            break
        }
    } catch {}
}
$PythonExe = $kivalasztottPython
if (-not $PythonExe) {
    throw 'Nem találtam 64 bites Python 3.11 vagy újabb telepítést. Telepítsd pip és Tcl/Tk támogatással, vagy add meg a python.exe útvonalát a -PythonExe kapcsolóval.'}
if ($Telepites) {
    & $PythonExe -I -m venv (Join-Path $projektMappa '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'A helyi Python-kornyezet letrehozasa nem sikerult.' }
    & $kornyezetPython -I -m pip install -r (Join-Path $pythonMappa 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'A csomagok telepitese nem sikerult. Ellenorizd az internetkapcsolatot.' }
    Write-Output 'A telepites elkeszult. Kovetkezo lepes: inditas\inditas.cmd -Ellenorzes'
    exit 0
}
$inditandoFajl = if ($Kiszolgalo) { 'szerver.py' } else { 'main.py' }
$programArgumentumok = @()
if ($ElsoAdmin) { $programArgumentumok += '--elso-admin' }
if ($Ellenorzes) {
    & $PythonExe -I -c "import sys; sys.path.insert(0,sys.argv[1]); import customtkinter,pyodbc,waitress,api,adatbazis; print('Python es csomagok: OK'); print('API port:',api.api_port()); print('SQL illeszto:',adatbazis.illeszto_neve()); print('SQL szerver:',adatbazis.SZERVER); print('Adatbazis:',adatbazis.ADATBAZIS)" $pythonMappa
} else {
    & $PythonExe -I -c "import sys,runpy; script=sys.argv[2]; sys.path.insert(0,sys.argv[1]); sys.argv=sys.argv[2:]; runpy.run_path(script,run_name='__main__')" $pythonMappa (Join-Path $pythonMappa $inditandoFajl) @programArgumentumok
}
if ($LASTEXITCODE -ne 0) { throw 'Az inditas hibaval allt le. Futtasd a telepito\telepites.cmd fajlt; tovabbi segitseg: README.md' }
