from contextlib import ExitStack
import importlib
"""Külön indítandó SQL Server-próba. MINDEN módosítást visszagörget.

python test_sql_integracio.py
Nem indítja el az unittest discovery, nem hoz létre tartós fiókot.
"""
from pathlib import Path
from unittest.mock import patch
import re
import adatbazis
import fiokok as f
import torzsadatok as t


def futtat():
    from api import SZERVER_OLDAL
    mod = SZERVER_OLDAL.set(True)
    import pyodbc
    kapcsolat = pyodbc.connect(
        f"DRIVER={{{adatbazis.illeszto_neve()}}};"
        f"SERVER={adatbazis.SZERVER};DATABASE={adatbazis.ADATBAZIS};"
        "Trusted_Connection=yes;TrustServerCertificate=yes;", timeout=5)
    kapcsolat.timeout = 10
    class ProbaKapcsolat:
        def cursor(self):
            return kapcsolat.cursor()
        def commit(self):
            pass
        def rollback(self):
            pass
        def close(self):
            pass
    try:
        k = kapcsolat.cursor()
        k.execute("SET XACT_ABORT ON; BEGIN TRANSACTION")
        sql = (Path(__file__).parents[2]/"sql"/"11_felhasznalok.sql").read_text(encoding="utf-8")
        for resz in re.split(r"(?im)^GO\s*$", sql):
            if resz.strip():
                k.execute(resz)
        sql = (Path(__file__).parents[2]/"sql"/"12_szerepkorok.sql").read_text(encoding="utf-8")
        for resz in re.split(r"(?im)^GO\s*$", sql):
            if resz.strip():
                k.execute(resz)
        sql = (Path(__file__).parents[2]/"sql"/"13_api_jogosultsagok.sql").read_text(encoding="utf-8")
        for resz in re.split(r"(?im)^GO\s*$", sql):
            if resz.strip():
                k.execute(resz)
        k.execute("DELETE FROM biztonsag.Felhasznalo")
        k.execute("EXECUTE AS USER=N'EszkozApiFuttato';")
        with ExitStack() as helyettesitesek:
            # A korábban importált közvetlen kapcsolathivatkozásokat is helyettesítem.
            for modulnev in ('adatbazis','eszkozok','beszerzesek','garanciak','halozat','karbantartasok','infrastruktura','partnerek'):
                modul = importlib.import_module(modulnev)
                if hasattr(modul,'kapcsolat_letrehozasa'):
                    helyettesitesek.enter_context(patch.object(modul,'kapcsolat_letrehozasa',return_value=ProbaKapcsolat()))
            # Egy üres, tranzakción belüli fióktáblán tesztelünk.
            f.letrehozas("teszt_admin","Admin teszt 12345",elso=True)
            f.belepes("teszt_admin","Admin teszt 12345")
            assert f.aktualis().Admin
            for _ in range(5):
                try:
                    f.belepes("teszt_admin","Hibas jelszo")
                except ValueError:
                    pass
            try:
                f.belepes("teszt_admin","Admin teszt 12345")
                raise AssertionError("Zárolás hiányzik")
            except ValueError:
                pass
            k.execute("UPDATE biztonsag.Felhasznalo SET Zarolva=NULL,Hibak=0")
            f.belepes("teszt_admin","Admin teszt 12345")
            f.letrehozas("teszt_user","Felhasznalo 12345")
            user = next(s for s in f.lista() if s.Nev=="teszt_user")
            kod = f.reset_kiadasa(user.FelhasznaloID)
            f.jelszo_visszaallitas("teszt_user",kod,"Uj felhasznalo 12345")
            try:
                f.jelszo_visszaallitas("teszt_user",kod,"Masik jelszo 12345")
                raise AssertionError("A kód újrahasználható")
            except ValueError:
                pass
            f.belepes("teszt_user","Uj felhasznalo 12345")
            try:
                f.lista()
                raise AssertionError("Admin jogosultság hiányzik")
            except PermissionError:
                pass
            f.jelszo_csere("Uj felhasznalo 12345","Sajat uj jelszo 12345")
            f.belepes("teszt_user","Sajat uj jelszo 12345")
            t.torzsadat_mentese("Gyarto",None,{"Nev":"__FELHASZNALO_TORZSADAT__"},True)
            try:
                f.letrehozas("tiltott_fiok","Hosszu jelszo 12345")
                raise AssertionError("A felhasználó fiókot hozhatott létre")
            except PermissionError:
                pass
            f.belepes("teszt_admin","Admin teszt 12345")
            f.letrehozas("teszt_viewer","Megtekinto 12345",megtekinto=True)
            f.belepes("teszt_viewer","Megtekinto 12345")
            assert f.aktualis().Megtekinto
            assert t.torzsadatok_listazasa("Gyarto")
            for modositas in (
                lambda: t.torzsadat_mentese("Gyarto",None,{"Nev":"__TILTOTT__"},True),
                lambda: adatbazis.tranzakcio(lambda cur: cur.execute("UPDATE torzs.Gyarto SET Nev=N'tiltott'")),
                lambda: __import__('garanciak').garancia_aktivitas(-1,False),
                lambda: f.fiok_modositasa(user.FelhasznaloID,True,True),
                lambda: f.reset_kiadasa(user.FelhasznaloID),
            ):
                try:
                    modositas()
                    raise AssertionError("Megtekintő írási jogosultságot kapott")
                except PermissionError:
                    pass
            f.jelszo_csere("Megtekinto 12345","Uj megtekinto 12345")
            f.belepes("teszt_admin","Admin teszt 12345")
            for tabla in t.TABLAK:
                sorok = t.torzsadatok_listazasa(tabla)
                if sorok:
                    s = sorok[0]
                    t.torzsadat_mentese(tabla,s[0],{n:getattr(s,n) for n in t.TABLAK[tabla]},bool(s.Aktiv))
            t.torzsadat_mentese("Gyarto",None,{"Nev":"__TRANZAKCIOS_TESZT__"},True)
            uj = next(s for s in t.torzsadatok_listazasa("Gyarto") if s.Nev=="__TRANZAKCIOS_TESZT__")
            t.torzsadat_mentese("Gyarto",uj[0],{"Nev":"__MODOSITOTT_TESZT__"},False)
            import eszkozok, infrastruktura, partnerek, beszerzesek, garanciak, karbantartasok, halozat
            eszkozok.eszkozok_lekerdezese()
            for tabla in infrastruktura.TABLAK:
                infrastruktura.listazas(tabla)
            beszerzesek.beszerzesek_listazasa()
            garanciak.garanciak_listazasa()
            karbantartasok.karbantartasok_listazasa()
            halozat.interfeszek_listazasa()
            halozat.ip_cimek_listazasa()
            partnerek.kapcsolatok_listazasa()
            # Új eszköz és üzembe helyezési dátum javítása valódi SQL-lel.
            k.execute("SELECT TOP 1 ModellID FROM torzs.Modell WHERE Aktiv=1")
            modell = k.fetchone()
            k.execute("SELECT TOP 1 StatuszID FROM torzs.Statusz WHERE Aktiv=1")
            statusz = k.fetchone()
            if modell and statusz:
                eszkozok.eszkoz_rogzitese("__INTEGRACIOS_TESZT__","",modell[0],statusz[0],"",uzembehelyezes="2024-02-29")
                k.execute("SELECT EszkozID,UzembehelyezesDatuma FROM eszkoz.Eszkoz WHERE LeltariSzam=?",("__INTEGRACIOS_TESZT__",))
                eszkoz = k.fetchone()
                assert str(eszkoz.UzembehelyezesDatuma)=="2024-02-29"
                eszkozok.eszkoz_modositasa(eszkoz.EszkozID,"__INTEGRACIOS_TESZT__","",modell[0],statusz[0],"",uzembehelyezes="")
                assert eszkozok.eszkoz_adatainak_lekerdezese(eszkoz.EszkozID).UzembehelyezesDatuma is None
            if "--gui" in __import__("sys").argv:
                import main
                app = main.EszkozNyilvantartas()
                app.withdraw()
                hibak = []
                app.report_callback_exception = lambda *e: hibak.append(e)
                for oldal in ("Főoldal","Eszközök","Infrastruktúra","Partnerek","Beszerzések","Garanciák","Karbantartások","Hálózat","Saját fiók","Törzsadatok"):
                    app.oldal_megjelenitese(oldal)
                    app.update_idletasks()
                app.destroy()
                assert not hibak, hibak
                print("Mind a 10 alkalmazásoldal felépítése sikeres.")
                for nev,jelszo in (("teszt_user","Sajat uj jelszo 12345"),("teszt_viewer","Uj megtekinto 12345")):
                    f.belepes(nev,jelszo)
                    app = main.EszkozNyilvantartas()
                    app.withdraw()
                    for oldal in ("Eszközök","Infrastruktúra","Partnerek","Beszerzések","Garanciák","Karbantartások","Hálózat","Törzsadatok","Saját fiók"):
                        app.oldal_megjelenitese(oldal)
                        app.update_idletasks()
                        def gombok(w):
                            for elem in w.winfo_children():
                                if isinstance(elem,main.ctk.CTkSegmentedButton):
                                    continue
                                if isinstance(elem,main.ctk.CTkButton):
                                    yield elem
                                yield from gombok(elem)
                        if nev=="teszt_viewer" and oldal!="Saját fiók":
                            for g in gombok(app.tartalom):
                                if g.cget("text") not in ("Keresés","Alaphelyzet","Törlés","Frissítés","Aktív","Inaktív"):
                                    assert g.cget("state")=="disabled", (oldal,g.cget("text"))
                    app.destroy()
                print("Felhasználó és megtekintő: oldalak és letiltott műveleti gombok OK.")
        print("SQL integráció: fiókok, zárolás, egyszer használható kód, jogosultságok, jelszócsere, törzsadatok, modullekérdezések: SIKER.")
    finally:
        f.kilepes()
        kapcsolat.rollback()
        kapcsolat.close()
        SZERVER_OLDAL.reset(mod)
        print("Az összes tesztmódosítás visszagörgetve.")


if __name__ == "__main__":
    futtat()
