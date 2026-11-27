from contextlib import ExitStack
import importlib
"""Külön futtatom a valódi HTTP/SQL próbát, minden tesztadatot visszagörgetek."""
from pathlib import Path
from unittest.mock import patch
import os
import re
import secrets
import threading
import pyodbc
import api
import adatbazis
import fiokok
from szerver import Kiszolgalo


def telepitett_proba():
    """A telepített jogosultságot valódi, külön SQL-kapcsolattal is ellenőrzöm."""
    from waitress import create_server
    mod = api.SZERVER_OLDAL.set(True)
    try:
        conn = adatbazis.kapcsolat_letrehozasa()
        try:
            sor = conn.cursor().execute("SELECT USER_NAME(), HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CREATE TABLE')").fetchone()
            assert sor[0]=='EszkozApiFuttato' and sor[1]==0
        finally:
            conn.close()
    finally:
        api.SZERVER_OLDAL.reset(mod)
    szerver = create_server(Kiszolgalo(),host='127.0.0.1',port=0,threads=2)
    szal = threading.Thread(target=szerver.run,daemon=True)
    szal.start()
    try:
        with patch.dict(os.environ,{'ESZKOZ_API_PORT':str(szerver.effective_port)}):
            assert isinstance(fiokok.van_fiok(),bool)
    finally:
        szerver.close()
        szerver.task_dispatcher.shutdown()
        szal.join(timeout=2)
    print('Telepitett API, valodi SQL-kapcsolat, korlatozott futtatoi jogosultsag: OK')


def futtat():
    from waitress import create_server
    # Csak a teszt előkészítéséhez használom a fejlesztői Windows SQL-jogot.
    conn = pyodbc.connect(f'DRIVER={{{adatbazis.illeszto_neve()}}};'
                          f'SERVER={adatbazis.SZERVER};DATABASE={adatbazis.ADATBAZIS};'
                          'Trusted_Connection=yes;TrustServerCertificate=yes;',timeout=5)
    conn.timeout = 10
    class ProbaKapcsolat:
        def cursor(self):return conn.cursor()
        def commit(self):pass
        def rollback(self):pass
        def close(self):pass
    szerver = szal = None
    regi_token = api._token
    try:
        k = conn.cursor()
        k.execute('BEGIN TRANSACTION')
        sql = (Path(__file__).parents[2]/'sql'/'13_api_jogosultsagok.sql').read_text(encoding='utf-8')
        for resz in re.split(r'(?im)^GO\s*$',sql):
            if resz.strip():k.execute(resz)
        elotag = '__api_'+secrets.token_hex(6)
        nevek = [elotag+s for s in ('_admin','_user','_viewer')]
        jelszo = secrets.token_urlsafe(24)
        for nev,admin,viewer in zip(nevek,(1,0,0),(0,0,1)):
            k.execute('INSERT INTO biztonsag.Felhasznalo (Nev,JelszoHash,Admin,Megtekinto) VALUES (?,?,?,?)',
                      (nev,fiokok.jelszo_hash(jelszo),admin,viewer))
        k.execute("EXECUTE AS USER=N'EszkozApiFuttato';")
        k.execute("SELECT HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CREATE TABLE'),"
                  "HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CONTROL')")
        assert tuple(k.fetchone()) == (0,0)
        app = Kiszolgalo()
        with ExitStack() as helyettesitesek:
            # A korábban importált közvetlen kapcsolathivatkozásokat is helyettesítem.
            for modulnev in ('adatbazis','eszkozok','beszerzesek','garanciak','halozat','karbantartasok','infrastruktura','partnerek'):
                modul = importlib.import_module(modulnev)
                if hasattr(modul,'kapcsolat_letrehozasa'):
                    helyettesitesek.enter_context(patch.object(modul,'kapcsolat_letrehozasa',return_value=ProbaKapcsolat()))
            szerver = create_server(app,host='127.0.0.1',port=0,threads=2,max_request_body_size=65536)
            szal = threading.Thread(target=szerver.run,daemon=True)
            szal.start()
            with patch.dict(os.environ,{'ESZKOZ_API_PORT':str(szerver.effective_port)}):
                import torzsadatok, eszkozok
                api._token = None
                try:
                    eszkozok.eszkozok_lekerdezese()
                    raise AssertionError('Belépés nélkül adatot adott vissza')
                except PermissionError:pass
                fiokok.belepes(nevek[0],jelszo)
                admin_token = api._token
                assert fiokok.aktualis().Admin
                assert len(fiokok.lista())>=3
                fiokok.belepes(nevek[1],jelszo)
                user_token = api._token
                assert not fiokok.aktualis().Admin
                torzsadatok.torzsadat_mentese('Gyarto',None,{'Nev':elotag},True)
                assert any(s.Nev==elotag for s in torzsadatok.torzsadatok_listazasa('Gyarto'))
                for tiltott in (lambda:fiokok.lista(),lambda:fiokok.letrehozas('tiltott',jelszo)):
                    try:
                        tiltott()
                        raise AssertionError('Felhasználó fiókkezelést kapott')
                    except PermissionError:pass
                fiokok.belepes(nevek[2],jelszo)
                viewer_token = api._token
                assert fiokok.aktualis().Megtekinto
                eszkozok.eszkozok_lekerdezese()
                eszkozok.fooldal_statisztika()
                for tiltott in (
                    lambda:torzsadatok.torzsadat_mentese('Gyarto',None,{'Nev':'tiltott'},True),
                    lambda:eszkozok.eszkoz_inaktivalasa(-1),
                    lambda:fiokok.reset_kiadasa(-1),
                ):
                    try:
                        tiltott()
                        raise AssertionError('Megtekintő írhatott')
                    except PermissionError:pass
                # A különböző kliensek tokenjei nem örökölhetik egymás szerepkörét.
                api._token = admin_token
                assert fiokok.aktualis().Admin
                viewer = next(s for s in fiokok.lista() if s.Nev==nevek[2])
                fiokok.fiok_modositasa(viewer.FelhasznaloID,False,True,megtekinto=True)
                api._token = viewer_token
                try:
                    fiokok.aktualis()
                    raise AssertionError('A régi token érvényes maradt')
                except PermissionError:pass
                api._token = user_token
                fiokok.jelszo_csere(jelszo,'Modositott jelszo 12345')
                assert not fiokok.aktualis().Admin
                fiokok.kilepes()
                assert api._token is None
                api._token = user_token
                try:
                    fiokok.aktualis()
                    raise AssertionError('Kijelentkezés után a token érvényes')
                except PermissionError:pass
                # Az oldalakat a valódi HTTP-kapcsolaton át is felépítem.
                if '--gui' in __import__('sys').argv:
                    import main
                    for index in (0,1,2):
                        fiokok.belepes(nevek[index],jelszo if index!=1 else 'Modositott jelszo 12345')
                        ablak = main.EszkozNyilvantartas()
                        ablak.withdraw()
                        for oldal in ('Főoldal','Eszközök','Infrastruktúra','Partnerek','Beszerzések',
                                      'Garanciák','Karbantartások','Hálózat','Törzsadatok','Saját fiók'):
                            ablak.oldal_megjelenitese(oldal)
                            ablak.update_idletasks()
                        ablak.destroy()
                        fiokok.kilepes()
        print('HTTP + SQL: 3 szerepkor, tokenek elvalasztasa/visszavonasa, irasi tiltas, korlatozott SQL-jogok: OK')
    finally:
        if szerver:
            szerver.close()
            szerver.task_dispatcher.shutdown()
        if szal:szal.join(timeout=2)
        api._token = regi_token
        conn.rollback()
        conn.close()
        print('Minden tesztadat es jogosultsagi probamodositas visszagorgetve.')


if __name__=='__main__':
    futtat()
