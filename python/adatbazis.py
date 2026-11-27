"""Adatbázis-kapcsolatok és tranzakciókezelés."""


import pyodbc
from api import BEALLITASOK

# A megszemélyesített SQL-kapcsolat nem kerül vissza a közös kapcsolatkészletbe.
pyodbc.pooling = False


SZERVER = BEALLITASOK.get('adatbazis','szerver',fallback='localhost')
ADATBAZIS = BEALLITASOK.get('adatbazis','nev',fallback='EszkozNyilvantartas')


# Automatikus beállításnál a gépen elérhető SQL Server ODBC-illesztőt választja ki.
def illeszto_neve():
    nev = BEALLITASOK.get('adatbazis','illeszto',fallback='auto')
    telepitett = pyodbc.drivers()
    if nev == 'auto':
        nev = next((n for n in ('ODBC Driver 18 for SQL Server','ODBC Driver 17 for SQL Server') if n in telepitett),None)
    if nev not in telepitett:
        raise RuntimeError('Telepitsd a Microsoft ODBC Driver 18 vagy 17 SQL Server illesztot.')
    return nev


# Közvetlen SQL-kapcsolatot csak a kiszolgálóoldali művelet nyithat.
def kapcsolat_letrehozasa():
    """Kapcsolódás a helyi SQL Server-adatbázishoz."""
    from api import SZERVER_OLDAL
    if not SZERVER_OLDAL.get():
        raise PermissionError("Az asztali program nem kapcsolódhat közvetlenül az SQL Serverhez.")
    beallitas = BEALLITASOK.get('adatbazis','tanusitvany_elfogadas',fallback='igen')
    tanusitvany = 'yes' if beallitas.lower() in ('igen','yes','true','1') else 'no'
    kapcsolat = pyodbc.connect(
        f"DRIVER={{{illeszto_neve()}}};"
        f"SERVER={SZERVER};"
        f"DATABASE={ADATBAZIS};"
        "Trusted_Connection=yes;"
        f"TrustServerCertificate={tanusitvany};",
        timeout=5
    )
    try:
        kapcsolat.timeout = 10
        # Az alkalmazás SQL-műveleteit korlátozott adatbázis-joggal végzem.
        kapcsolat.cursor().execute("EXECUTE AS USER = N'EszkozApiFuttato';")
        return kapcsolat
    except Exception:
        kapcsolat.close()
        raise


def lekerdezes(sql, parameterek=(), egy=False, vedett=True):
    """SQL-lekérdezés biztonságos kapcsolatlezárással."""
    kapcsolat = kapcsolat_letrehozasa()
    try:
        kurzor = kapcsolat.cursor()
        if vedett:
            from fiokok import jogosult
            jogosult(kurzor)
        kurzor.execute(sql, parameterek)
        return kurzor.fetchone() if egy else kurzor.fetchall()
    finally:
        kapcsolat.close()


def tranzakcio(muvelet, vedett=True):
    """Kurzorral végzett művelet: siker esetén commit, hibánál rollback."""
    kapcsolat = kapcsolat_letrehozasa()
    try:
        kurzor = kapcsolat.cursor()
        if vedett:
            from fiokok import jogosult
            jogosult(kurzor, iras=True)
        eredmeny = muvelet(kurzor)
        kapcsolat.commit()
        return eredmeny
    except Exception:
        kapcsolat.rollback()
        raise
    finally:
        kapcsolat.close()


if __name__ == "__main__":
    try:
        kapcsolat = kapcsolat_letrehozasa()
        try:
            nev = kapcsolat.cursor().execute("SELECT DB_NAME()").fetchone()[0]
            print(f"Sikeres kapcsolat! Adatbázis: {nev}")
        finally:
            kapcsolat.close()
    except pyodbc.Error as hiba:
        print(f"Nem sikerült csatlakozni: {hiba}")
