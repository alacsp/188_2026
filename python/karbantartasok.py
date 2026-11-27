from ellenorzes import szoveg as _szoveg
"""Karbantartások és a hozzájuk tartozó felület kezelése."""


from datetime import datetime
from ellenorzes import penzosszeg
from adatbazis import kapcsolat_letrehozasa, lekerdezes as _lista
from felulet_seged import FelugroAblak, muveleti_gomb
from tkinter import messagebox
import customtkinter as ctk


# A karbantartási műveletek az eszközökhöz rögzített munkákat és költségeket kezelik.
def karbantartasok_listazasa():
    return _lista("""
        SELECT k.KarbantartasID, k.EszkozID, k.KarbantartasTipusID,
               e.LeltariSzam, kt.Nev AS Tipus,
               k.BejelentesDatuma, k.KezdesDatuma, k.BefejezesDatuma,
               k.Leiras, k.Eredmeny, k.Koltseg, k.Penznem, k.Megjegyzes
        FROM eszkoz.Karbantartas AS k
        JOIN eszkoz.Eszkoz AS e ON k.EszkozID = e.EszkozID
        JOIN torzs.KarbantartasTipus AS kt
            ON k.KarbantartasTipusID = kt.KarbantartasTipusID
        ORDER BY COALESCE(k.BejelentesDatuma, k.KezdesDatuma,
                          k.BefejezesDatuma) DESC, k.KarbantartasID DESC
    """)


def karbantartas_valasztok(eszkoz_id=None, tipus_id=None):
    return (
        _lista("""
            SELECT EszkozID, LeltariSzam, Aktiv FROM eszkoz.Eszkoz
            WHERE Aktiv = 1 OR EszkozID = ? ORDER BY LeltariSzam
        """, (eszkoz_id,)),
        _lista("""
            SELECT KarbantartasTipusID, Nev, Aktiv FROM torzs.KarbantartasTipus
            WHERE Aktiv = 1 OR KarbantartasTipusID = ? ORDER BY Nev
        """, (tipus_id,))
    )


def _idopont(ertek, nev):
    szoveg = str(ertek or "").strip()
    if not szoveg:
        return None
    try:
        datum = datetime.fromisoformat(szoveg)
        if datum.tzinfo is not None:
            raise ValueError
        return datum
    except ValueError as hiba:
        raise ValueError(f"{nev}: ÉÉÉÉ-HH-NN ÓÓ:PP formátum szükséges.") from hiba


def _koltseg(ertek):
    return penzosszeg(ertek, "költség")



def karbantartas_mentese(azonosito, eszkoz_id, tipus_id,
                         bejelentes, kezdes, befejezes,
                         leiras, eredmeny, koltseg, penznem, megjegyzes):
    if eszkoz_id is None or tipus_id is None:
        raise ValueError("Eszköz és karbantartástípus megadása kötelező.")
    bejelentes = _idopont(bejelentes, "Bejelentés ideje")
    kezdes = _idopont(kezdes, "Kezdés ideje")
    befejezes = _idopont(befejezes, "Befejezés ideje")
    if kezdes is not None and befejezes is not None and befejezes < kezdes:
        raise ValueError("A befejezés nem lehet a kezdés előtt.")
    if befejezes is not None and kezdes is None:
        raise ValueError("Befejezéshez a kezdés időpontját is add meg.")
    if bejelentes is not None and kezdes is not None and kezdes < bejelentes:
        raise ValueError("A kezdés nem lehet a bejelentés előtt.")
    koltseg = _koltseg(koltseg)
    penznem = (penznem or "").strip().upper()
    if penznem and (len(penznem) != 3 or not penznem.isascii()
                    or not penznem.isalpha()):
        raise ValueError("A pénznem hárombetűs kód legyen, pl. HUF.")
    if (koltseg is None) != (not penznem):
        raise ValueError("A költséget és a pénznemet együtt add meg.")
    leiras = _szoveg(leiras, 1000, "leírás")
    eredmeny = _szoveg(eredmeny, 1000, "eredmény")
    megjegyzes = _szoveg(megjegyzes, 500, "megjegyzés")
    ertekek = (eszkoz_id, tipus_id, bejelentes, kezdes, befejezes,
               leiras, eredmeny, koltseg, penznem or None, megjegyzes)

    kapcsolat = kapcsolat_letrehozasa()
    try:
        kurzor = kapcsolat.cursor()
        from fiokok import jogosult
        jogosult(kurzor, iras=True)
        regi_eszkoz = regi_tipus = None
        if azonosito is not None:
            kurzor.execute("""
                SELECT EszkozID, KarbantartasTipusID FROM eszkoz.Karbantartas
                WHERE KarbantartasID = ?
            """, (azonosito,))
            regi = kurzor.fetchone()
            if regi is None:
                raise ValueError("A karbantartás nem található.")
            regi_eszkoz, regi_tipus = regi
        if eszkoz_id != regi_eszkoz:
            kurzor.execute("""
                SELECT 1 FROM eszkoz.Eszkoz WHERE EszkozID = ? AND Aktiv = 1
            """, (eszkoz_id,))
            if kurzor.fetchone() is None:
                raise ValueError("A kiválasztott eszköz nem aktív.")
        if tipus_id != regi_tipus:
            kurzor.execute("""
                SELECT 1 FROM torzs.KarbantartasTipus
                WHERE KarbantartasTipusID = ? AND Aktiv = 1
            """, (tipus_id,))
            if kurzor.fetchone() is None:
                raise ValueError("A karbantartástípus nem aktív.")
        if azonosito is None:
            kurzor.execute("""
                INSERT INTO eszkoz.Karbantartas
                    (EszkozID, KarbantartasTipusID, BejelentesDatuma,
                     KezdesDatuma, BefejezesDatuma, Leiras, Eredmeny,
                     Koltseg, Penznem, Megjegyzes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ertekek)
        else:
            kurzor.execute("""
                UPDATE eszkoz.Karbantartas
                SET EszkozID = ?, KarbantartasTipusID = ?, BejelentesDatuma = ?,
                    KezdesDatuma = ?, BefejezesDatuma = ?, Leiras = ?,
                    Eredmeny = ?, Koltseg = ?, Penznem = ?, Megjegyzes = ?
                WHERE KarbantartasID = ?
            """, (*ertekek, azonosito))
            if kurzor.rowcount != 1:
                raise ValueError("A karbantartás módosítása nem sikerült.")
        kapcsolat.commit()
    except Exception:
        kapcsolat.rollback()
        raise
    finally:
        kapcsolat.close()



# A képernyő listázza és állapot szerint szűri a karbantartási eseményeket.
class KarbantartasokFelulet(ctk.CTkFrame):
    def __init__(self, szulo):
        super().__init__(szulo, fg_color="transparent")
        self.keresett = ""
        self.allapot = "Összes"
        self.megjelenites()

    @staticmethod
    def _allapot(r):
        return ("Lezárt" if r.BefejezesDatuma else
                "Folyamatban" if r.KezdesDatuma else
                "Bejelentve" if r.BejelentesDatuma else "Tervezett")

    def megjelenites(self):
        for elem in self.winfo_children():
            elem.destroy()
        try:
            adatok = karbantartasok_listazasa()
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba), parent=self)
            return
        fejlec = ctk.CTkFrame(self, fg_color="transparent")
        fejlec.pack(fill="x", padx=10, pady=10)
        muveleti_gomb(fejlec, text="+ Új karbantartás", width=160,
                      command=self.urlap).pack(side="left", padx=5)
        kereso = ctk.CTkEntry(fejlec, width=195, placeholder_text="Keresés...")
        kereso.pack(side="left", padx=5)
        kereso.insert(0, self.keresett)
        valaszto = ctk.CTkOptionMenu(
            fejlec, values=["Összes", "Tervezett", "Bejelentve", "Folyamatban", "Lezárt"],
            width=135, command=self.allapot_valtas)
        valaszto.pack(side="left", padx=5)
        valaszto.set(self.allapot)

        def kereses():
            self.keresett = kereso.get().strip()
            self.megjelenites()

        ctk.CTkButton(fejlec, text="Keresés", width=80,
                      command=kereses).pack(side="left", padx=5)
        kereso.bind("<Return>", lambda _e: kereses())
        ctk.CTkButton(fejlec, text="Alaphelyzet", width=100,
                      command=self.alaphelyzet).pack(side="left", padx=5)
        sorok = [r for r in adatok if self.allapot == "Összes"
                 or self._allapot(r) == self.allapot]
        if self.keresett:
            keresett = self.keresett.casefold()
            sorok = [r for r in sorok if any(keresett in str(v or "").casefold()
                    for v in (r.LeltariSzam, r.Tipus, r.Leiras,
                              r.Eredmeny, r.Megjegyzes))]
        ctk.CTkLabel(self, text=f"Karbantartások: {len(sorok)} / {len(adatok)}",
                     anchor="w").pack(fill="x", padx=15, pady=5)
        tabla = ctk.CTkScrollableFrame(self)
        tabla.pack(fill="both", expand=True, padx=10, pady=5)
        fejlecek = ("Eszköz", "Típus", "Bejelentés", "Kezdés", "Befejezés", "Állapot", "Művelet")
        meretek = (110, 165, 125, 125, 125, 95, 105)
        for oszlop, nev in enumerate(fejlecek):
            ctk.CTkLabel(tabla, text=nev, width=meretek[oszlop], anchor="w",
                         font=ctk.CTkFont(weight="bold")
                         ).grid(row=0, column=oszlop, padx=4, pady=8, sticky="w")
        for index, r in enumerate(sorok, start=1):
            ertekek = (r.LeltariSzam, r.Tipus,
                       r.BejelentesDatuma.strftime("%Y-%m-%d %H:%M") if r.BejelentesDatuma else "–",
                       r.KezdesDatuma.strftime("%Y-%m-%d %H:%M") if r.KezdesDatuma else "–",
                       r.BefejezesDatuma.strftime("%Y-%m-%d %H:%M") if r.BefejezesDatuma else "–",
                       self._allapot(r))
            for oszlop, ertek in enumerate(ertekek):
                ctk.CTkLabel(tabla, text=str(ertek), width=meretek[oszlop],
                             anchor="w", wraplength=meretek[oszlop]
                             ).grid(row=index, column=oszlop, padx=4, pady=5, sticky="w")
            muveleti_gomb(tabla, text="Szerkesztés", width=100,
                          command=lambda rekord=r: self.urlap(rekord)
                          ).grid(row=index, column=6, padx=4, pady=5)
        if not sorok:
            ctk.CTkLabel(tabla, text="Nincs megjeleníthető karbantartás.").grid(
                row=1, column=0, columnspan=7, pady=25)

    def allapot_valtas(self, ertek):
        self.allapot = ertek
        self.megjelenites()

    def alaphelyzet(self):
        self.keresett = ""
        self.allapot = "Összes"
        self.megjelenites()

    @staticmethod
    def mezo(keret, felirat, ertek=""):
        ctk.CTkLabel(keret, text=felirat, anchor="w").pack(fill="x", pady=(10, 3))
        mezo = ctk.CTkEntry(keret)
        mezo.pack(fill="x")
        mezo.insert(0, str("" if ertek is None else ertek))
        return mezo

    @staticmethod
    def szovegdoboz(keret, felirat, ertek=""):
        ctk.CTkLabel(keret, text=felirat, anchor="w").pack(fill="x", pady=(10, 3))
        mezo = ctk.CTkTextbox(keret, height=70)
        mezo.pack(fill="x")
        mezo.insert("1.0", str("" if ertek is None else ertek))
        return mezo

    @staticmethod
    def valaszto(keret, felirat, opciok, kijelolt=None):
        ctk.CTkLabel(keret, text=felirat, anchor="w").pack(fill="x", pady=(10, 3))
        menu = ctk.CTkOptionMenu(keret, values=list(opciok))
        menu.pack(fill="x")
        menu.set(next((nev for nev, az in opciok.items() if az == kijelolt),
                      next(iter(opciok))))
        return menu

    def urlap(self, rekord=None):
        try:
            eszkozok, tipusok = karbantartas_valasztok(
                rekord.EszkozID if rekord else None,
                rekord.KarbantartasTipusID if rekord else None)
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba), parent=self)
            return
        if not eszkozok or not tipusok:
            messagebox.showwarning("Hiányzó adat",
                                   "Eszköz és karbantartástípus szükséges.", parent=self)
            return
        eszkoz_opciok = {f"{e.LeltariSzam} (ID: {e.EszkozID})": e.EszkozID
                         for e in eszkozok}
        tipus_opciok = {f"{t.Nev} (ID: {t.KarbantartasTipusID})": t.KarbantartasTipusID
                        for t in tipusok}
        ablak = FelugroAblak(self)
        ablak.title("Karbantartás szerkesztése" if rekord else "Új karbantartás")
        ablak.geometry("760x730")
        ablak.minsize(670, 600)
        ablak.transient(self.winfo_toplevel())
        keret = ctk.CTkScrollableFrame(ablak)
        keret.pack(fill="both", expand=True, padx=20, pady=20)
        ablak.grab_set()
        eszkoz = self.valaszto(keret, "Eszköz *", eszkoz_opciok,
                              rekord.EszkozID if rekord else None)
        tipus = self.valaszto(keret, "Karbantartás típusa *", tipus_opciok,
                             rekord.KarbantartasTipusID if rekord else None)
        bejelentes = self.mezo(keret, "Bejelentés (ÉÉÉÉ-HH-NN ÓÓ:PP)",
                               rekord.BejelentesDatuma if rekord else "")
        kezdes = self.mezo(keret, "Kezdés (ÉÉÉÉ-HH-NN ÓÓ:PP)",
                           rekord.KezdesDatuma if rekord else "")
        befejezes = self.mezo(keret, "Befejezés (ÉÉÉÉ-HH-NN ÓÓ:PP)",
                              rekord.BefejezesDatuma if rekord else "")
        leiras = self.szovegdoboz(keret, "Leírás", rekord.Leiras if rekord else "")
        eredmeny = self.szovegdoboz(keret, "Eredmény", rekord.Eredmeny if rekord else "")
        koltseg = self.mezo(keret, "Költség (pl. 12500,50)",
                            rekord.Koltseg if rekord else "")
        penznem = self.mezo(keret, "Pénznem (pl. HUF)",
                            rekord.Penznem if rekord else "")
        megjegyzes = self.szovegdoboz(keret, "Megjegyzés", rekord.Megjegyzes if rekord else "")

        def mentes():
            try:
                karbantartas_mentese(
                    rekord.KarbantartasID if rekord else None,
                    eszkoz_opciok[eszkoz.get()], tipus_opciok[tipus.get()],
                    bejelentes.get(), kezdes.get(), befejezes.get(),
                    leiras.get("1.0", "end").strip(),
                    eredmeny.get("1.0", "end").strip(),
                    koltseg.get(), penznem.get(),
                    megjegyzes.get("1.0", "end").strip())
            except Exception as hiba:
                messagebox.showerror("Mentési hiba", str(hiba), parent=ablak)
                return
            ablak.destroy()
            self.megjelenites()
            messagebox.showinfo("Siker", "A karbantartás mentve.", parent=self)

        muveleti_gomb(keret, text="Mentés", height=40,
                      command=mentes).pack(fill="x", pady=20)


from api import bekotes
bekotes(globals(), "karbantartasok")
