"""Külön futtatandó grafikus regressziós próba, adatbázis nélkül."""
from unittest.mock import patch
import customtkinter as ctk
from fiokok import Belepes, idozitok_leallitasa
from felulet_seged import FelugroAblak


def futtat():
    with patch('fiokok.van_fiok', return_value=True):
        for siker in (False,True,False,True):
            w = Belepes()
            w.withdraw()
            # A gyermekwidget saját Tcl-parancsa: korábban ezt a főablak
            # after_cancel hívása törölte, aztán a gyermek újra törölte.
            w.jelszo.after(5000,lambda: None)
            w.nev.insert(0,'teszt')
            w.jelszo.insert(0,'Teszt jelszo 12345')
            if siker:
                with patch('fiokok.belepes'):
                    w.belep()
                assert w.siker
            else:
                # Ugyanezt a destroy metódust hívja a Windows X gombja.
                w.destroy()
                assert not w.siker
    root = ctk.CTk()
    root.withdraw()
    ablak = FelugroAblak(root)
    assert str(ablak.transient()) == str(root)
    ablak.after(300,root.quit)
    root.mainloop()
    assert ablak._eloter_id is None
    ablak.destroy()
    # Gyors bezáráskor a késleltetett előtérbe hozás se maradjon futva.
    ablak = FelugroAblak(root)
    ablak.destroy()
    root.after(300,root.quit)
    root.mainloop()
    idozitok_leallitasa(root)
    root.destroy()
    print('X-bezaras, sikeres belepes, gyermeki idozitok, felugro ablak es gyors bezaras: OK')


if __name__ == '__main__':
    futtat()
