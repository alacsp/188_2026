# Szükséges

- 64 bites Windows, Python 3.12, pip és Tcl/Tk
- SQL Server és Microsoft ODBC Driver 18 (a 17-es is megfelelő)
- Internet a Python-csomagok első telepítéséhez

# Telepítés és indítás

1. Másold a mappát írható helyre, majd állítsd be az SQL-példányt a `beallitasok.ini` fájlban.
2. Futtasd a `telepito\adatbazis_telepites.cmd` fájlt. Meglévő adatbázist nem ír felül.
3. Futtasd a `telepito\telepites.cmd` fájlt a Python-környezet és a csomagok telepítéséhez.
4. Hozd létre az első admint: `inditas\elso_admin.cmd`.
5. Napi használatkor indítsd el az `inditas\szerver_inditas.cmd`, majd az `inditas\inditas.cmd` fájlt.

Sikertelen első telepítés után javítsd a hibát. Ha a telepítő üres EszkozNyilvantartas adatbázist hagyott hátra, ellenőrzés után töröld, majd futtasd újra a telepítőt.
A csomag tiszta adatbázishoz készült; korábbi adatok átviteléhez külön adatbázismentés kell. A Power BI-riport külön nyílik meg, új gépen az adatforrását be kell állítani.

# Tesztek

A projekt főmappában PowerShellben parancssorban kell futtatni a következő sorokat:

  $env:PYTHONPATH = (Resolve-Path .\python).Path
  .\.venv\Scripts\python.exe -m unittest discover -s .\python\teszt -p "test_*.py"
  .\.venv\Scripts\python.exe .\python\teszt\test_ablak_eletciklus.py
  .\.venv\Scripts\python.exe .\python\teszt\test_api_sql.py
  .\.venv\Scripts\python.exe .\python\teszt\test_sql_integracio.py
  
