"""Az engedélyezett műveletek továbbítása a helyi kiszolgálónak."""
from contextvars import ContextVar
from configparser import ConfigParser
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal
from functools import wraps
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

SZERVER_OLDAL = ContextVar('szerver_oldal', default=False)
_token = None

BEALLITASOK = ConfigParser(interpolation=None)
BEALLITASOK.read(Path(__file__).parents[1]/'beallitasok.ini',encoding='utf-8-sig')


def api_port():
    port = int(os.environ.get('ESZKOZ_API_PORT',BEALLITASOK.get('alkalmazas','api_port',fallback='8765')))
    if not 1 <= port <= 65535:
        raise ValueError('Az API portja 1 es 65535 kozotti egesz szam legyen.')
    return port

# Csak ezeket a név szerinti műveleteket engedem át, SQL-t soha.
# o: olvasás, i: írás, a: admin, n: bejelentkezés nélkül is hívható.
MUVELETEK = {
    'fiokok': {
        'van_fiok':'n', 'belepes':'n', 'jelszo_visszaallitas':'n',
        'kilepes':'o', 'aktualis':'o', 'jelszo_csere':'o',
        'lista':'a', 'letrehozas':'a', 'fiok_modositasa':'a', 'reset_kiadasa':'a'},
    'eszkozok': {
        'eszkozok_lekerdezese':'o','torzsadatok_lekerdezese':'o',
        'eszkoz_adatainak_lekerdezese':'o','helyek_lekerdezese':'o','fooldal_statisztika':'o',
        'eszkoz_rogzitese':'i','eszkoz_modositasa':'i','eszkoz_inaktivalasa':'i',
        'eszkoz_visszaallitasa':'i','eszkoz_helyenek_modositasa':'i'},
    'torzsadatok': {'torzsadatok_listazasa':'o','torzsadat_mentese':'i'},
    'infrastruktura': {'listazas':'o','valasztasi_adatok':'o',
        'telephely_mentese':'i','terem_mentese':'i','hely_mentese':'i','aktivitas_valtasa':'i'},
    'partnerek': {'partnerek_listazasa':'o','kapcsolatok_listazasa':'o','kapcsolat_valasztok':'o',
        'partner_mentese':'i','partner_aktivitas':'i','kapcsolat_mentese':'i','kapcsolat_lezarasa':'i'},
    'beszerzesek': {'beszerzesek_listazasa':'o','beszerzes_valasztok':'o','beszerzes_mentese':'i'},
    'garanciak': {'garanciak_listazasa':'o','garancia_valasztok':'o','garancia_mentese':'i','garancia_aktivitas':'i'},
    'karbantartasok': {'karbantartasok_listazasa':'o','karbantartas_valasztok':'o','karbantartas_mentese':'i'},
    'halozat': {'interfeszek_listazasa':'o','ip_cimek_listazasa':'o',
        'interfesz_eszkozok':'o','ip_interfeszek':'o','interfesz_mentese':'i',
        'interfesz_aktivitas':'i','ip_mentese':'i','ip_aktivitas':'i'},
}


# Az adatbázissor oszlopnév és sorszám alapján is elérhető.
class Adatsor:
    def __init__(self, nevek, ertekek):
        self._nevek, self._ertekek = nevek, ertekek
    def __getitem__(self, index):
        return self._ertekek[index]
    def __iter__(self):
        return iter(self._ertekek)
    def __getattr__(self, nev):
        try:
            return self._ertekek[self._nevek.index(nev)]
        except ValueError:
            raise AttributeError(nev) from None


# A JSON-kéréshez dátumokat, összegeket és adatbázissorokat alakít át.
def csomagol(ertek):
    if isinstance(ertek, Adatsor):
        return {'__sor__':ertek._nevek, 'ertekek':ertek._ertekek}
    if hasattr(ertek, 'cursor_description'):
        return {'__sor__':[c[0] for c in ertek.cursor_description], 'ertekek':list(ertek)}
    if isinstance(ertek, datetime):
        return {'__datumido__':ertek.isoformat()}
    if isinstance(ertek, date):
        return {'__datum__':ertek.isoformat()}
    if isinstance(ertek, Decimal):
        return {'__osszeg__':str(ertek)}
    raise TypeError('Nem továbbítható adattípus.')


# A szerializált értékeket visszaalakítja a megfelelő Python-típusokra.
def kibont(ertek):
    if '__sor__' in ertek:
        return Adatsor(ertek['__sor__'], ertek['ertekek'])
    if '__datumido__' in ertek:
        return datetime.fromisoformat(ertek['__datumido__'])
    if '__datum__' in ertek:
        return date.fromisoformat(ertek['__datum__'])
    if '__osszeg__' in ertek:
        return Decimal(ertek['__osszeg__'])
    return ertek


class NincsAtiranyitas(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


# A kliens a művelet nevét és paramétereit a helyi API-végpontra küldi.
def hivas(modul, nev, args, kwargs):
    global _token
    kilepes = (modul,nev)==('fiokok','kilepes')
    if kilepes and _token is None:
        return None
    # A helyi próba forgalmát nem küldöm proxyn keresztül.
    port = api_port()
    cim = f'http://127.0.0.1:{port}/muvelet'
    fejlec = {'Content-Type':'application/json'}
    if _token:
        fejlec['Authorization'] = 'Bearer '+_token
    kerestest = json.dumps({'modul':modul,'nev':nev,'args':args,'kwargs':kwargs},
                           default=csomagol, allow_nan=False).encode()
    keres = Request(cim, data=kerestest, headers=fejlec, method='POST')
    if (modul,nev)==('fiokok','belepes'):
        _token = None
    try:
        with build_opener(ProxyHandler({}), NincsAtiranyitas()).open(keres, timeout=20) as valasz:
            adat = json.loads(valasz.read(), object_hook=kibont)
    except HTTPError as h:
        if kilepes:
            return None
        adat = json.loads(h.read())
        tipus = PermissionError if h.code in (401,403) else ValueError if h.code==400 else RuntimeError
        raise tipus(adat.get('hiba','A kiszolgáló elutasította a műveletet.')) from None
    except (URLError, TimeoutError):
        if kilepes:
            return None
        raise ConnectionError('A helyi kiszolgáló nem elérhető. Indítsd a szerver_inditas.cmd fájlt.') from None
    finally:
        if kilepes:
            _token = None
    if (modul,nev)==('fiokok','belepes'):
        _token = adat['token']
    elif (modul,nev)==('fiokok','kilepes'):
        _token = None
    return adat.get('eredmeny')


# Az adatkezelő függvényeket kliensoldali API-hívásra cseréli.
def bekotes(nevtar, modul):
    for nev in MUVELETEK[modul]:
        eredeti = nevtar[nev]
        @wraps(eredeti)
        def tovabbit(*args, _nev=nev, _f=eredeti, **kwargs):
            if SZERVER_OLDAL.get():
                return _f(*args, **kwargs)
            return hivas(modul, _nev, args, kwargs)
        nevtar[nev] = tovabbit
