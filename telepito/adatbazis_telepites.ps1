param([string]$Szerver, [string]$Adatbazis, [switch]$Ellenorzes)
$ErrorActionPreference = 'Stop'
$projektMappa = Split-Path -Parent $PSScriptRoot

Add-Type -AssemblyName System.Data
$beallitas = @{}
$szakasz = ''
foreach ($sor in [System.IO.File]::ReadAllLines((Join-Path $projektMappa 'beallitasok.ini'))) {
    if ($sor -match '^\s*\[([^\]]+)\]') { $szakasz = $Matches[1]; continue }
    if ($szakasz -eq 'adatbazis' -and $sor -match '^\s*([^;#=]+?)\s*=\s*(.*?)\s*$') {
        $beallitas[$Matches[1]] = $Matches[2]
    }
}
if (-not $Szerver) { $Szerver = $beallitas['szerver'] }
if (-not $Adatbazis) { $Adatbazis = $beallitas['nev'] }
if (-not $Szerver -or -not $Adatbazis -or $Adatbazis.Length -gt 128) {
    throw 'Hibas vagy hianyzo szerver/adatbazis: ellenorizd a beallitasok.ini fajlt.'
}
if ($Adatbazis -in @('master','model','msdb','tempdb')) { throw 'Rendszeradatbazis nem valaszthato.' }
$sqlMappa = Join-Path $projektMappa 'sql'
$lepesek = @(
    '02_semak.sql', '03_torzstabla.sql', '04_infrastruktura_tabla.sql',
    '05_eszkoz_tabla.sql', '06_partner_tabla.sql', '07_beszerzes_karbantartas.sql',
    '08_halozat.sql', '09_torzsadatok.sql', '10_powerbi_nezetek.sql',
    '11_felhasznalok.sql', '12_szerepkorok.sql', '13_api_jogosultsagok.sql'
)
foreach ($fajl in $lepesek) {
    if (-not (Test-Path -LiteralPath (Join-Path $sqlMappa $fajl))) { throw "Hianyzo SQL-fajl: $fajl" }
}
$cim = [System.Data.SqlClient.SqlConnectionStringBuilder]::new()
$cim['Data Source'] = $Szerver
$cim['Initial Catalog'] = 'master'
$cim['Integrated Security'] = $true
$cim['Encrypt'] = $true
$cim['TrustServerCertificate'] = $beallitas['tanusitvany_elfogadas'] -in @('igen','yes','true','1')
$cim['Connect Timeout'] = 10
$cim['Application Name'] = 'EszkozNyilvantartas V2 telepito'
$kapcsolat = [System.Data.SqlClient.SqlConnection]::new($cim.ConnectionString)
$tranzakcio = $null
$letrehozva = $false
try {
    $kapcsolat.Open()
    $parancs = $kapcsolat.CreateCommand()
    $parancs.CommandText = 'SELECT DB_ID(@nev)'
    $null = $parancs.Parameters.Add('@nev',[System.Data.SqlDbType]::NVarChar,128)
    $parancs.Parameters['@nev'].Value = $Adatbazis
    $letezik = $parancs.ExecuteScalar() -isnot [System.DBNull]
    $parancs.Dispose()
    if ($Ellenorzes) {
        Write-Output "SQL-kapcsolat: OK. Szerver: $Szerver. Adatbazis: $Adatbazis. Letezik: $letezik"
        exit 0
    }
    if ($letezik) { throw 'Az adatbazis mar letezik. A telepito nem torli es nem irja felul.' }
    $idezojel = '[' + $Adatbazis.Replace(']',']]') + ']'
    $parancs = $kapcsolat.CreateCommand()
    $parancs.CommandTimeout = 60
    $parancs.CommandText = "CREATE DATABASE $idezojel"
    $null = $parancs.ExecuteNonQuery()
    $parancs.Dispose()
    $letrehozva = $true
    $kapcsolat.ChangeDatabase($Adatbazis)
    $tranzakcio = $kapcsolat.BeginTransaction()
    foreach ($fajl in $lepesek) {
        Write-Output "Telepitem: $fajl"
        $sql = [System.IO.File]::ReadAllText((Join-Path $sqlMappa $fajl))
        $sql = $sql.Replace('USE EszkozNyilvantartas;', "USE $idezojel;")
        foreach ($resz in [regex]::Split($sql, '(?im)^[ \t]*GO[ \t]*(?:--[^\r\n]*)?\r?$')) {
            if ([string]::IsNullOrWhiteSpace($resz)) { continue }
            $parancs = $kapcsolat.CreateCommand()
            $parancs.Transaction = $tranzakcio
            $parancs.CommandTimeout = 60
            $parancs.CommandText = $resz
            $null = $parancs.ExecuteNonQuery()
            $parancs.Dispose()
        }
    }
    $tranzakcio.Commit()
    $tranzakcio.Dispose()
    $tranzakcio = $null
    Write-Output "A tiszta adatbazis elkeszult: $Adatbazis"
    Write-Output 'Kovetkezo lepes: telepito\telepites.cmd, majd inditas\elso_admin.cmd.'
} catch {
    if ($tranzakcio) {
        try { $tranzakcio.Rollback() } catch { }
    }
    if ($letrehozva) {
        Write-Warning 'A szerkezet/adatfeltoltes nem keszult el. Az uj adatbazis megmaradhatott uresen; a telepito nem torli automatikusan.'
    }
    throw
} finally {
    $kapcsolat.Dispose()
}
