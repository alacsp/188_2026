"""Közös ablakok és szerkesztési gombok kezelése."""


import customtkinter as ctk
from tkinter import TclError


# Közös felugróablak-viselkedés: előtérbe hozás és biztonságos bezárás.
class FelugroAblak(ctk.CTkToplevel):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.transient(master.winfo_toplevel())
        self._eloter_id = self.after(200, self.eloterbe)

    def eloterbe(self):
        self._eloter_id = None
        self.lift()
        self.focus_set()

    def destroy(self):
        if self._eloter_id is not None:
            try:
                self.after_cancel(self._eloter_id)
            except TclError:
                pass
            self._eloter_id = None
        super().destroy()



# A gomb csak akkor jelenik meg aktívként, ha a munkamenet jogosult a műveletre.
def muveleti_gomb(master, **kwargs):
    import fiokok
    felhasznalo = getattr(master.winfo_toplevel(), 'felhasznalo', None)
    if felhasznalo is None:
        felhasznalo = fiokok.aktualis()
    if felhasznalo.Megtekinto:
        kwargs['state'] = 'disabled'
    return ctk.CTkButton(master, **kwargs)
