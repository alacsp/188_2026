import io
import hashlib
import json
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch
import api
import adatbazis
from szerver import Kiszolgalo, Beleptetes


def keres(app, modul='torzsadatok', nev='torzsadat_mentese', args=None, kwargs=None, **env):
    test = json.dumps({'modul':modul,'nev':nev,'args':args or [],'kwargs':kwargs or {}}).encode()
    alap = {'REMOTE_ADDR':'127.0.0.1','HTTP_HOST':'127.0.0.1:8765',
            'REQUEST_METHOD':'POST','PATH_INFO':'/muvelet','CONTENT_TYPE':'application/json',
            'CONTENT_LENGTH':str(len(test)),'wsgi.input':io.BytesIO(test)}
    alap.update(env)
    return app.keres(alap)


class ApiHatarTeszt(unittest.TestCase):
    def test_beallitott_port_es_ertekhatar(self):
        import os
        with patch.dict(os.environ,{'ESZKOZ_API_PORT':'18765'}):
            self.assertEqual(api.api_port(),18765)
        with patch.dict(os.environ,{'ESZKOZ_API_PORT':'0'}):
            with self.assertRaises(ValueError):
                api.api_port()

    def setUp(self):
        self.app = Kiszolgalo()

    def test_belepes_nelkul_nincs_iras(self):
        self.assertEqual(keres(self.app,args=['Gyarto',None,{'Nev':'uj'},True])[0],401)

    def test_nincs_szabad_sql_vegpont(self):
        for modul,nev in (('adatbazis','lekerdezes'),('fiokok','jelszo_hash'),('os','system')):
            self.assertEqual(keres(self.app,modul,nev,args=['SELECT 1'])[0],404)

    def test_bongeszo_es_tavoli_gep_tiltva(self):
        for env in ({'HTTP_ORIGIN':'https://pelda.hu'}, {'HTTP_HOST':'tamado.hu'}, {'REMOTE_ADDR':'192.0.2.1'}):
            self.assertEqual(keres(self.app,**env)[0],403)

    def test_elso_admin_nem_hozhato_letre_apirol(self):
        self.assertEqual(keres(self.app,'fiokok','letrehozas',args=['admin','Teszt jelszo 12345'],kwargs={'elso':True})[0],403)

    def test_tul_nagy_keres_tiltva(self):
        self.assertEqual(keres(self.app,CONTENT_LENGTH='65537')[0],413)

    def test_token_nelkul_nincs_olvasas(self):
        self.assertEqual(keres(self.app,'eszkozok','eszkozok_lekerdezese')[0],401)

    def test_ervenytelen_parameterek(self):
        self.assertEqual(keres(self.app,'eszkozok','eszkozok_lekerdezese',kwargs={'sql':'DROP TABLE x'})[0],400)

    def test_klienstol_nincs_sql_kapcsolat(self):
        mod = api.SZERVER_OLDAL.set(False)
        try:
            with patch.object(adatbazis.pyodbc,'connect') as kapcsolat:
                with self.assertRaises(PermissionError):
                    adatbazis.kapcsolat_letrehozasa()
                kapcsolat.assert_not_called()
        finally:
            api.SZERVER_OLDAL.reset(mod)

    def test_sor_datum_osszeg_atvitel(self):
        sor = api.Adatsor(['Datum','Ar'],[date(2024,2,29),Decimal('123.45')])
        vissza = json.loads(json.dumps(sor,default=api.csomagol),object_hook=api.kibont)
        self.assertEqual(vissza.Datum,date(2024,2,29))
        self.assertEqual(vissza[1],Decimal('123.45'))

    def test_lejart_token_tiltva(self):
        token='teszt-token'
        self.app.munkamenetek[hashlib.sha256(token.encode()).hexdigest()] = Beleptetes(None,-100000,-100000)
        self.assertEqual(keres(self.app,'eszkozok','eszkozok_lekerdezese',HTTP_AUTHORIZATION='Bearer '+token)[0],401)


if __name__=='__main__':
    unittest.main()
