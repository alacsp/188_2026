"""Belépés és engedélyezett műveletek ellenőrzése."""
from collections import defaultdict, deque
from dataclasses import dataclass
from hashlib import sha256
import importlib
import inspect
import json
import logging
import secrets
import threading
import time
from api import MUVELETEK, SZERVER_OLDAL, csomagol, kibont, api_port

NAPLO = logging.getLogger('eszkoz_api')


@dataclass
class Beleptetes:
    munkamenet: object
    kezdet: float
    utolso: float


# A WSGI-kiszolgáló ellenőrzi a kéréseket, a munkamenetet és a műveleti jogosultságot.
class Kiszolgalo:
    def __init__(self):
        self.zar = threading.RLock()
        self.munkamenetek = {}
        self.probak = defaultdict(deque)
        self.modulok = {nev:importlib.import_module(nev) for nev in MUVELETEK}

    def __call__(self, environ, start_response):
        statusz, adat = self.keres(environ)
        valasz = json.dumps(adat,default=csomagol,ensure_ascii=False,allow_nan=False).encode()
        start_response(f'{statusz} '+{200:'OK',400:'Bad Request',401:'Unauthorized',403:'Forbidden',
                       404:'Not Found',405:'Method Not Allowed',413:'Content Too Large',
                       429:'Too Many Requests',500:'Internal Server Error'}[statusz],
                       [('Content-Type','application/json; charset=utf-8'),
                        ('Content-Length',str(len(valasz))),('Cache-Control','no-store'),
                        ('X-Content-Type-Options','nosniff')])
        return [valasz]

    def keres(self, env):
        # Biztonsági okból a prototípus csak helyi kapcsolatokat fogad.
        if env.get('REMOTE_ADDR') not in ('127.0.0.1','::1'):
            return 403, {'hiba':'Csak helyi kapcsolat engedélyezett.'}
        if env.get('HTTP_ORIGIN') or env.get('HTTP_HOST','').split(':')[0] not in ('127.0.0.1','localhost'):
            return 403, {'hiba':'Ez a kérés nem engedélyezett.'}
        if env.get('PATH_INFO')=='/allapot' and env.get('REQUEST_METHOD')=='GET':
            return 200, {'szolgaltatas':'eszkoz_api','verzio':1}
        if env.get('PATH_INFO')!='/muvelet':
            return 404, {'hiba':'Ismeretlen végpont.'}
        if env.get('REQUEST_METHOD')!='POST':
            return 405, {'hiba':'Csak POST kérés engedélyezett.'}
        if env.get('CONTENT_TYPE','').split(';')[0]!='application/json':
            return 400, {'hiba':'JSON kérés szükséges.'}
        try:
            hossz = int(env.get('CONTENT_LENGTH','0'))
            if not 0 < hossz <= 65536:
                return 413, {'hiba':'Túl nagy vagy üres kérés.'}
            adat = json.loads(env['wsgi.input'].read(hossz),object_hook=kibont,
                              parse_constant=lambda x: (_ for _ in ()).throw(ValueError()))
            if not isinstance(adat,dict) or set(adat)!={'modul','nev','args','kwargs'}:
                raise ValueError()
            modul, nev = adat['modul'], adat['nev']
            if not isinstance(modul,str) or not isinstance(nev,str):
                raise ValueError()
            jogosultsag = MUVELETEK.get(modul,{}).get(nev)
            if jogosultsag is None:
                return 404, {'hiba':'Ismeretlen művelet.'}
            args, kwargs = adat['args'], adat['kwargs']
            if not isinstance(args,list) or not isinstance(kwargs,dict) or len(args)>32 or len(kwargs)>32:
                raise ValueError()
            muvelet = getattr(self.modulok[modul],nev).__wrapped__
            param = inspect.signature(muvelet).bind(*args,**kwargs)
            param.apply_defaults()
            # Első admint csak a kiszolgáló helyi parancsával hozok létre.
            if modul=='fiokok' and nev=='letrehozas' and param.arguments['elso']:
                return 403, {'hiba':'Az első admin létrehozása csak a kiszolgálón engedélyezett.'}
        except (ValueError,TypeError,KeyError,UnicodeError,RecursionError):
            return 400, {'hiba':'Hibás kérés vagy hiányzó paraméter.'}

        fiokok = self.modulok['fiokok']
        hitelesites = env.get('HTTP_AUTHORIZATION','')
        tokenhash = sha256(hitelesites[7:].encode()).hexdigest() if hitelesites.startswith('Bearer ') else None
        # A régi üzleti függvények munkamenetét zárral választom el a többi kéréstől.
        with self.zar:
            most = time.monotonic()
            for az,s in list(self.munkamenetek.items()):
                if most-s.utolso>1800 or most-s.kezdet>28800:
                    del self.munkamenetek[az]
            if jogosultsag=='n':
                probak = self.probak[(env['REMOTE_ADDR'],nev)]
                while probak and most-probak[0]>60:
                    probak.popleft()
                if len(probak)>=20:
                    return 429, {'hiba':'Túl sok kérés. Várj egy percet.'}
                probak.append(most)
            s = self.munkamenetek.get(tokenhash)
            if jogosultsag!='n' and s is None:
                return 401, {'hiba':'Jelentkezz be újra.'}
            regi_mod = SZERVER_OLDAL.set(True)
            fiokok._munkamenet = s.munkamenet if s else None
            try:
                if jogosultsag!='n':
                    fiokok.tranzakcio(lambda k: fiokok.jogosult(k,admin=jogosultsag=='a',iras=jogosultsag=='i'))
                eredmeny = muvelet(*args,**kwargs)
                valasz = {'eredmeny':eredmeny}
                if (modul,nev)==('fiokok','belepes'):
                    token = secrets.token_urlsafe(32)
                    if len(self.munkamenetek)>=1000:
                        del self.munkamenetek[min(self.munkamenetek,key=lambda az:self.munkamenetek[az].utolso)]
                    self.munkamenetek[sha256(token.encode()).hexdigest()] = Beleptetes(fiokok._munkamenet,most,most)
                    valasz['token'] = token
                elif (modul,nev)==('fiokok','kilepes'):
                    self.munkamenetek.pop(tokenhash,None)
                elif s:
                    s.munkamenet, s.utolso = fiokok._munkamenet,most
                # A naplóba sem jelszó, sem token, sem kód nem kerül.
                NAPLO.info('muvelet=%s.%s fiok=%s eredmeny=OK',modul,nev,
                           getattr(fiokok._munkamenet,'az',None))
                return 200,valasz
            except PermissionError:
                NAPLO.warning('muvelet=%s.%s eredmeny=TILTVA',modul,nev)
                return 403,{'hiba':'Nincs megfelelő jogosultságod, vagy lejárt a munkameneted.'}
            except ValueError as h:
                return 400,{'hiba':str(h)}
            except Exception as h:
                NAPLO.error('muvelet=%s.%s hibatipus=%s',modul,nev,type(h).__name__)
                return 500,{'hiba':'A kiszolgáló nem tudta végrehajtani a műveletet. Ellenőrizd a kiszolgáló naplóját.'}
            finally:
                fiokok._munkamenet = None
                SZERVER_OLDAL.reset(regi_mod)


# A szolgáltatás kizárólag a helyi gépen figyelő HTTP-kiszolgálót indít.
def inditas():
    import os
    from pathlib import Path
    from waitress import serve
    logging.basicConfig(filename=Path(__file__).parents[1]/'szerver.log',level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    app = Kiszolgalo()
    if '--elso-admin' in __import__('sys').argv:
        from getpass import getpass
        mod = SZERVER_OLDAL.set(True)
        try:
            nev = input('Elso admin felhasznaloneve: ')
            jelszo = getpass('Jelszo (legalabb 12 karakter): ')
            if jelszo != getpass('Jelszo ujra: '):
                raise ValueError('A ket jelszo elter.')
            app.modulok['fiokok'].letrehozas(nev,jelszo,elso=True)
            print('Az adminfiok letrejott.')
        finally:
            SZERVER_OLDAL.reset(mod)
        return
    print('A helyi kiszolgalo fut. Ezt az ablakot hagyd nyitva.')
    serve(app,host='127.0.0.1',port=api_port(),
          threads=4,max_request_body_size=65536,channel_timeout=15,connection_limit=32,
          clear_untrusted_proxy_headers=True)


if __name__=='__main__':
    inditas()
