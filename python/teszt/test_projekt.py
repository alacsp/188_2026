"""Adatbázis nélkül futtatható regressziós tesztek.

A próbakapcsolat csak a tranzakciók és paraméterek viselkedését ellenőrzi;
az SQL Server sémájának és zárolásainak ellenőrzését nem helyettesíti.
"""

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

try:
    import pyodbc
except ModuleNotFoundError:
    sys.modules["pyodbc"] = types.ModuleType("pyodbc")

import adatbazis
import beszerzesek
import ellenorzes
import garanciak
import karbantartasok
import partnerek
import halozat


class MezoEllenorzesTeszt(unittest.TestCase):
    def test_kozos_szovegellenorzes(self):
        for ertek in (None, "", "   "):
            self.assertIsNone(ellenorzes.szoveg(ertek,5,"megjegyzés"))
        self.assertEqual(ellenorzes.szoveg("  abc  ",3,"megjegyzés"),"abc")
        with self.assertRaises(ValueError):
            ellenorzes.szoveg("abcd",3,"megjegyzés")

    def test_nullas_osszeg_szamkent_is_megmarad(self):
        for fuggveny in (beszerzesek._ar, karbantartasok._koltseg):
            for ertek in (0, Decimal("0"), "0", "0,00"):
                with self.subTest(fuggveny=fuggveny.__name__, ertek=ertek):
                    self.assertEqual(fuggveny(ertek), Decimal("0.00"))

    def test_osszeg_formazas(self):
        for fuggveny in (beszerzesek._ar, karbantartasok._koltseg):
            self.assertEqual(fuggveny("125 000,50"), Decimal("125000.50"))
            self.assertEqual(fuggveny("125\u00a0000,50"), Decimal("125000.50"))
            self.assertEqual(fuggveny("9999999999999999.99"), Decimal("9999999999999999.99"))
            self.assertIsNone(fuggveny(None))
            self.assertIsNone(fuggveny(" "))

    def test_hibas_osszegek(self):
        for fuggveny in (beszerzesek._ar, karbantartasok._koltseg):
            for ertek in ("NaN", "sNaN", "Infinity", "-1", "1.001", "abc", "1e9999", "1e-9999", "10000000000000000"):
                with self.subTest(fuggveny=fuggveny.__name__, ertek=ertek):
                    with self.assertRaises(ValueError):
                        fuggveny(ertek)

    def test_datumok(self):
        self.assertEqual(beszerzesek._datum("2024-02-29"), date(2024, 2, 29))
        self.assertIsNone(beszerzesek._datum(""))
        for ertek in ("2023-02-29", "20241022", "2024-W01-1", "", None):
            with self.subTest(ertek=ertek):
                with self.assertRaises(ValueError):
                    garanciak._datum(ertek, "garancia kezdete")

    def test_garancia_idorend(self):
        with self.assertRaises(ValueError):
            garanciak.garancia_mentese(None, 1, "2024-02-02", "2024-02-01", None, "", "")

    def test_karbantartas_idorend(self):
        for bejelentes, kezdes, befejezes in (
            ("2024-02-02", "2024-02-01", ""),
            ("", "2024-02-02", "2024-02-01"),
            ("", "", "2024-02-01"),
        ):
            with self.subTest(kezdes=kezdes, befejezes=befejezes):
                with self.assertRaises(ValueError):
                    karbantartasok.karbantartas_mentese(None, 1, 1, bejelentes, kezdes, befejezes, "", "", "", "", "")

    def test_halozati_cimek(self):
        self.assertEqual(halozat._ip_es_prefix("2001:0db8::1", "128"), ("2001:db8::1", 128))
        self.assertEqual(halozat._ip_es_prefix("192.0.2.1", "0"), ("192.0.2.1", 0))
        for cim, prefix in (("192.0.2.1", "33"), ("2001:db8::1", "129"), ("hibas", "24")):
            with self.assertRaises(ValueError):
                halozat._ip_es_prefix(cim, prefix)
        self.assertEqual(halozat._mac("aa-bb-cc-dd-ee-ff"), "AA:BB:CC:DD:EE:FF")


class TranzakcioTeszt(unittest.TestCase):
    def test_sikeres_commit_es_lezaras(self):
        kapcsolat = Mock()
        with patch.object(adatbazis, "kapcsolat_letrehozasa", return_value=kapcsolat):
            self.assertEqual(adatbazis.tranzakcio(lambda k: 42, vedett=False), 42)
        kapcsolat.commit.assert_called_once()
        kapcsolat.rollback.assert_not_called()
        kapcsolat.close.assert_called_once()

    def test_hibanal_rollback_es_lezaras(self):
        kapcsolat = Mock()
        def hibas(k):
            raise ValueError("Próbahiba")
        with patch.object(adatbazis, "kapcsolat_letrehozasa", return_value=kapcsolat):
            with self.assertRaisesRegex(ValueError, "Próbahiba"):
                adatbazis.tranzakcio(hibas, vedett=False)
        kapcsolat.commit.assert_not_called()
        kapcsolat.rollback.assert_called_once()
        kapcsolat.close.assert_called_once()

    def test_lekerdezesi_hibanal_is_lezar(self):
        kapcsolat = Mock()
        kapcsolat.cursor.return_value.execute.side_effect = RuntimeError("Próbahiba")
        with patch.object(adatbazis, "kapcsolat_letrehozasa", return_value=kapcsolat):
            with self.assertRaises(RuntimeError):
                adatbazis.lekerdezes("SELECT 1", vedett=False)
        kapcsolat.close.assert_called_once()


class PartnerKapcsolatTeszt(unittest.TestCase):
    def test_szerkeszteskor_regi_inaktiv_referenciak_megmaradhatnak(self):
        kurzor = Mock()
        kurzor.rowcount = 1
        kurzor.fetchone.side_effect = [(10, 20, 30), (1,), (1,), (1,), (0,)]
        with patch.object(partnerek, "_tranzakcio", side_effect=lambda f: f(kurzor)):
            partnerek.kapcsolat_mentese(1, 10, 20, 30, "2024-01-01", "2024-02-01", "")
        hivasok = kurzor.execute.call_args_list
        for hivas, vart in zip(hivasok[1:4], ((10, 10), (20, 20), (30, 30))):
            self.assertEqual(hivas.args[1], vart)

    def test_uj_inaktiv_referencia_elutasitva(self):
        kurzor = Mock()
        kurzor.fetchone.side_effect = [(10, 20, 30), None]
        with patch.object(partnerek, "_tranzakcio", side_effect=lambda f: f(kurzor)):
            with self.assertRaisesRegex(ValueError, "eszköz nem aktív"):
                partnerek.kapcsolat_mentese(1, 99, 20, 30, "2024-01-01", "", "")
        self.assertEqual(kurzor.execute.call_args_list[1].args[1], (99, 10))

    def test_valasztok_korabbival_egyutt(self):
        with patch.object(partnerek, "_lekerdezes", return_value=[]) as lista:
            partnerek.kapcsolat_valasztok(10, 20, 30)
        self.assertEqual([h.args[1] for h in lista.call_args_list], [(20,), (10,), (30,)])

    def test_nemletezo_kapcsolat_nem_mentheto(self):
        kurzor = Mock()
        kurzor.fetchone.return_value = None
        with patch.object(partnerek, "_tranzakcio", side_effect=lambda f: f(kurzor)):
            with self.assertRaisesRegex(ValueError, "nem található"):
                partnerek.kapcsolat_mentese(1, 10, 20, 30, "2024-01-01", "", "")
        self.assertEqual(kurzor.execute.call_count, 1)


class ForrasTeszt(unittest.TestCase):
    def test_minden_modul_szintaktikailag_helyes(self):
        for fajl in Path(__file__).parents[1].glob("*.py"):
            with self.subTest(fajl=fajl.name):
                ast.parse(fajl.read_text(encoding="utf-8"), filename=str(fajl))




def setUpModule():
    from api import SZERVER_OLDAL
    global _teszt_mod
    _teszt_mod = SZERVER_OLDAL.set(True)


def tearDownModule():
    from api import SZERVER_OLDAL
    SZERVER_OLDAL.reset(_teszt_mod)


if __name__ == "__main__":
    unittest.main()
