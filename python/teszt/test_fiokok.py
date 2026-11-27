import unittest
from types import SimpleNamespace as Sor
from unittest.mock import Mock, patch
import fiokok as f
import adatbazis
import torzsadatok as t


class JelszoTeszt(unittest.TestCase):
    def tearDown(self):
        f.kilepes()

    def test_so_es_ellenorzes(self):
        a = f.jelszo_hash("Sajat jelszo 12345")
        b = f.jelszo_hash("Sajat jelszo 12345")
        self.assertNotEqual(a,b)
        self.assertNotIn("Sajat",a)
        self.assertTrue(f.jelszo_egyezik("Sajat jelszo 12345",a))
        self.assertFalse(f.jelszo_egyezik("mas jelszo",a))
        self.assertFalse(f.jelszo_egyezik("akarmi","serult"))

    def test_jelszohosszak(self):
        for v in ("", "rovid", "x"*257):
            with self.assertRaises(ValueError):
                f.jelszo_hash(v)

    def test_belepes_nelkul_tiltott(self):
        with self.assertRaises(PermissionError):
            f.jogosult(Mock())

    def test_lejart_munkamenet(self):
        f._munkamenet = f.Munkamenet(1,1)
        k = Mock()
        k.fetchone.return_value = None
        with self.assertRaises(PermissionError):
            f.jogosult(k)

    def test_felhasznalo_nem_admin(self):
        f._munkamenet = f.Munkamenet(1,1)
        k = Mock()
        k.fetchone.return_value = Sor(Nev="user", Admin=False)
        with self.assertRaises(PermissionError):
            f.jogosult(k, True)

    def test_utolso_admin_megmarad(self):
        k = Mock()
        k.fetchall.return_value = [Sor(FelhasznaloID=1,Admin=True,Aktiv=True)]
        with patch.object(f,"tranzakcio",side_effect=lambda fn: fn(k)), patch.object(f,"jogosult"):
            with self.assertRaisesRegex(ValueError,"utolsó"):
                f.fiok_modositasa(1,False,False)

    def test_visszaallito_kod_csak_hashkent(self):
        k = Mock(rowcount=1)
        with patch.object(f,"tranzakcio",side_effect=lambda fn: fn(k)), patch.object(f,"jogosult"):
            kod = f.reset_kiadasa(2)
        self.assertNotIn(kod, str(k.execute.call_args))
        self.assertIn(f.hashlib.sha256(kod.encode()).hexdigest(),str(k.execute.call_args))

    def test_visszaallitas_ervenytelen(self):
        k = Mock(rowcount=0)
        with patch.object(f,"tranzakcio",side_effect=lambda fn: fn(k)):
            with self.assertRaisesRegex(ValueError,"lejárt"):
                f.jelszo_visszaallitas("user","ervenytelen","Uj jelszo 12345")

    def test_vedett_adatbazismuvelet_visszagorget(self):
        kapcsolat = Mock()
        f.kilepes()
        with patch.object(adatbazis,"kapcsolat_letrehozasa",return_value=kapcsolat):
            with self.assertRaises(PermissionError):
                adatbazis.tranzakcio(lambda k: k.execute("UPDATE tiltott"))
        kapcsolat.rollback.assert_called_once()
        kapcsolat.commit.assert_not_called()

    def test_torzsadat_engedelylista(self):
        with self.assertRaises(KeyError):
            t.torzsadatok_listazasa("Gyarto; DROP TABLE eszkoz.Eszkoz")
        with self.assertRaisesRegex(ValueError,"Kötelező"):
            t.torzsadat_mentese("Gyarto",None,{"Nev":""},True)

    def test_megtekinto_olvashat_de_nem_irhat(self):
        f._munkamenet = f.Munkamenet(1,1)
        k = Mock()
        k.fetchone.return_value = Sor(Nev="viewer",Admin=False,Megtekinto=True)
        self.assertEqual(f.jogosult(k).Nev,"viewer")
        with self.assertRaises(PermissionError):
            f.jogosult(k,iras=True)

    def test_felhasznalo_irhat_de_fiokokat_nem_kezelhet(self):
        f._munkamenet = f.Munkamenet(1,1)
        k = Mock()
        k.fetchone.return_value = Sor(Nev="user",Admin=False,Megtekinto=False)
        self.assertEqual(f.jogosult(k,iras=True).Nev,"user")
        with self.assertRaises(PermissionError):
            f.jogosult(k,admin=True)

    def test_admin_minden_jogosultsag(self):
        f._munkamenet = f.Munkamenet(1,1)
        k = Mock()
        k.fetchone.return_value = Sor(Nev="admin",Admin=True,Megtekinto=False)
        self.assertEqual(f.jogosult(k,admin=True,iras=True).Nev,"admin")

    def test_ellentmondo_szerepkor_tiltott(self):
        with self.assertRaises(ValueError):
            f.letrehozas("hibas","Hosszu jelszo 12345",admin=True,megtekinto=True)
        with self.assertRaises(ValueError):
            f.fiok_modositasa(1,True,True,megtekinto=True)




def setUpModule():
    from api import SZERVER_OLDAL
    global _teszt_mod
    _teszt_mod = SZERVER_OLDAL.set(True)


def tearDownModule():
    from api import SZERVER_OLDAL
    SZERVER_OLDAL.reset(_teszt_mod)


if __name__ == "__main__":
    unittest.main()
