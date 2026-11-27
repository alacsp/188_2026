from ellenorzes import szoveg as _szoveg
"""Beszerzések és a hozzájuk tartozó felület kezelése."""


from ellenorzes import datum as datum_ellenorzes, penzosszeg
from adatbazis import kapcsolat_letrehozasa, lekerdezes as _lekerdezes
from felulet_seged import FelugroAblak, muveleti_gomb
from tkinter import messagebox
import customtkinter as ctk


# A lekérdezések és mentések az eszközbeszerzések üzleti szabályait kezelik.
def beszerzesek_listazasa():
    """Minden beszerzést megjelenít, inaktív eszköz és beszállító esetén is."""
    return _lekerdezes("""
        SELECT b.BeszerzesID, b.EszkozID, b.BeszallitoID,
               e.LeltariSzam, p.Nev AS Beszallito,
               b.BeszerzesDatuma, b.BeszerzesiAr, b.Penznem,
               b.SzamlaSzam, b.MegrendelesSzam, b.Megjegyzes
        FROM eszkoz.Beszerzes AS b
        INNER JOIN eszkoz.Eszkoz AS e ON b.EszkozID = e.EszkozID
        LEFT JOIN partner.Beszallito AS p
            ON b.BeszallitoID = p.BeszallitoID
        ORDER BY b.BeszerzesDatuma DESC, b.BeszerzesID DESC
    """)


def beszerzes_valasztok(eszkoz_id=None, beszallito_id=None):
    """Aktív választható adatok; szerkesztéskor a régi inaktív érték is látható."""
    eszkozok = _lekerdezes("""
        SELECT EszkozID, LeltariSzam, Aktiv
        FROM eszkoz.Eszkoz
        WHERE Aktiv = 1 OR EszkozID = ?
        ORDER BY LeltariSzam
    """, (eszkoz_id,))
    beszallitok = _lekerdezes("""
        SELECT BeszallitoID, Nev, Aktiv
        FROM partner.Beszallito
        WHERE Aktiv = 1 OR BeszallitoID = ?
        ORDER BY Nev
    """, (beszallito_id,))
    return eszkozok, beszallitok


def _datum(szoveg):
    return datum_ellenorzes(szoveg, "beszerzés dátuma")


def _ar(szoveg):
    return penzosszeg(szoveg, "beszerzési ár")



def beszerzes_mentese(azonosito, eszkoz_id, beszallito_id, datum,
                      ar, penznem, szamlaszam, megrendelesszam, megjegyzes):
    """Új beszerzés rögzítése vagy meglévő adatainak módosítása."""
    if eszkoz_id is None:
        raise ValueError("Eszköz megadása kötelező.")

    datum = _datum(datum)
    ar = _ar(ar)
    penznem = (penznem or "").strip().upper()
    if penznem and (len(penznem) != 3 or not penznem.isascii()
                    or not penznem.isalpha()):
        raise ValueError("A pénznem hárombetűs kód legyen (pl. HUF vagy EUR).")
    if (ar is None) != (not penznem):
        raise ValueError("A beszerzési árat és a pénznemet együtt add meg.")

    ertekek = (
        eszkoz_id, beszallito_id, datum, ar, penznem or None,
        _szoveg(szamlaszam, 100, "számlaszám"),
        _szoveg(megrendelesszam, 100, "megrendelésszám"),
        _szoveg(megjegyzes, 500, "megjegyzés"),
    )

    kapcsolat = kapcsolat_letrehozasa()
    try:
        kurzor = kapcsolat.cursor()
        from fiokok import jogosult
        jogosult(kurzor, iras=True)
        regi_eszkoz, regi_beszallito = None, None

        if azonosito is not None:
            kurzor.execute("""
                SELECT EszkozID, BeszallitoID
                FROM eszkoz.Beszerzes WITH (UPDLOCK, HOLDLOCK)
                WHERE BeszerzesID = ?
            """, (azonosito,))
            regi = kurzor.fetchone()
            if regi is None:
                raise ValueError("A szerkesztendő beszerzés nem található.")
            regi_eszkoz, regi_beszallito = regi.EszkozID, regi.BeszallitoID

        # Új kapcsolatnál aktív adatot kérek, a korábbi hivatkozást megtartom.
        if azonosito is None or eszkoz_id != regi_eszkoz:
            kurzor.execute("""
                SELECT 1 FROM eszkoz.Eszkoz WHERE EszkozID = ? AND Aktiv = 1
            """, (eszkoz_id,))
            if kurzor.fetchone() is None:
                raise ValueError("A kiválasztott eszköz nem aktív vagy nem található.")

        if beszallito_id is not None and (azonosito is None or beszallito_id != regi_beszallito):
            kurzor.execute("""
                SELECT 1 FROM partner.Beszallito
                WHERE BeszallitoID = ? AND Aktiv = 1
            """, (beszallito_id,))
            if kurzor.fetchone() is None:
                raise ValueError("A kiválasztott beszállító nem aktív vagy nem található.")

        if azonosito is None:
            kurzor.execute("""
                INSERT INTO eszkoz.Beszerzes
                    (EszkozID, BeszallitoID, BeszerzesDatuma, BeszerzesiAr,
                     Penznem, SzamlaSzam, MegrendelesSzam, Megjegyzes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ertekek)
        else:
            kurzor.execute("""
                UPDATE eszkoz.Beszerzes
                SET EszkozID = ?, BeszallitoID = ?, BeszerzesDatuma = ?,
                    BeszerzesiAr = ?, Penznem = ?, SzamlaSzam = ?,
                    MegrendelesSzam = ?, Megjegyzes = ?
                WHERE BeszerzesID = ?
            """, (*ertekek, azonosito))
            if kurzor.rowcount != 1:
                raise ValueError("A beszerzés módosítása nem sikerült.")

        kapcsolat.commit()
    except Exception:
        kapcsolat.rollback()
        raise
    finally:
        kapcsolat.close()



# A képernyő listázza, szűri, létrehozza és szerkeszti a beszerzési rekordokat.
class BeszerzesekFelulet(ctk.CTkFrame):
    def __init__(self, szulo):
        super().__init__(szulo, fg_color="transparent")
        self.keresett = ""
        self.penznem_szuro = "Összes"
        self.megjelenites()

    def megjelenites(self):
        for elem in self.winfo_children():
            elem.destroy()

        vezerlok = ctk.CTkFrame(self, fg_color="transparent")
        vezerlok.pack(fill="x", padx=10, pady=(0, 12))

        muveleti_gomb(
            vezerlok, text="+ Új beszerzés", width=130,
            command=self.beszerzes_urlap
        ).pack(side="left", padx=(0, 12))

        kereso = ctk.CTkEntry(
            vezerlok, width=210, placeholder_text="Keresés..."
        )
        kereso.pack(side="left", padx=5)
        kereso.insert(0, self.keresett)

        try:
            osszes = beszerzesek_listazasa()
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba), parent=self)
            return

        penznemek = ["Összes"] + sorted({s.Penznem for s in osszes if s.Penznem})
        if self.penznem_szuro not in penznemek:
            self.penznem_szuro = "Összes"
        valaszto = ctk.CTkOptionMenu(
            vezerlok, values=penznemek, width=110,
            command=self.penznem_valtas
        )
        valaszto.pack(side="left", padx=5)
        valaszto.set(self.penznem_szuro)

        def kereses():
            self.keresett = kereso.get().strip()
            self.megjelenites()

        ctk.CTkButton(
            vezerlok, text="Keresés", width=85, command=kereses
        ).pack(side="left", padx=5)
        kereso.bind("<Return>", lambda _esemeny: kereses())
        ctk.CTkButton(
            vezerlok, text="Alaphelyzet", width=100,
            command=self.szuro_torlese
        ).pack(side="left", padx=5)

        sorok = [s for s in osszes if self.penznem_szuro == "Összes"
                 or s.Penznem == self.penznem_szuro]
        if self.keresett:
            keresett = self.keresett.casefold()
            sorok = [s for s in sorok if any(
                keresett in str(ertek or "").casefold()
                for ertek in (s.LeltariSzam, s.Beszallito, s.SzamlaSzam,
                              s.MegrendelesSzam, s.Megjegyzes)
            )]

        ctk.CTkLabel(
            self, text=f"Beszerzések: {len(sorok)} / {len(osszes)}",
            anchor="w"
        ).pack(fill="x", padx=10, pady=6)

        tabla = ctk.CTkScrollableFrame(self)
        tabla.pack(fill="both", expand=True, padx=10, pady=5)

        fejlecek = ("Leltári szám", "Beszállító", "Dátum", "Összeg",
                    "Számlaszám", "Műveletek")
        szelessegek = (125, 170, 110, 125, 150, 105)
        for oszlop, nev in enumerate(fejlecek):
            ctk.CTkLabel(
                tabla, text=nev, width=szelessegek[oszlop],
                anchor="w", font=ctk.CTkFont(weight="bold")
            ).grid(row=0, column=oszlop, padx=7, pady=9, sticky="w")

        if not sorok:
            ctk.CTkLabel(
                tabla, text="Nincs a feltételeknek megfelelő beszerzés."
            ).grid(row=1, column=0, columnspan=len(fejlecek), pady=25)
            return

        for sorindex, rekord in enumerate(sorok, start=1):
            osszeg = (
                f"{rekord.BeszerzesiAr:,.2f} {rekord.Penznem or ''}".replace(",", " ")
                if rekord.BeszerzesiAr is not None else "–"
            )
            adatok = (
                rekord.LeltariSzam,
                rekord.Beszallito or "Nincs megadva",
                str(rekord.BeszerzesDatuma or "–"),
                osszeg,
                rekord.SzamlaSzam or "–",
            )
            for oszlop, ertek in enumerate(adatok):
                ctk.CTkLabel(
                    tabla, text=str(ertek), width=szelessegek[oszlop],
                    anchor="w", wraplength=szelessegek[oszlop]
                ).grid(row=sorindex, column=oszlop, padx=7, pady=6, sticky="w")

            muveleti_gomb(
                tabla, text="Szerkesztés", width=100,
                command=lambda r=rekord: self.beszerzes_urlap(r)
            ).grid(row=sorindex, column=5, padx=7, pady=6)

    def penznem_valtas(self, ertek):
        self.penznem_szuro = ertek
        self.megjelenites()

    def szuro_torlese(self):
        self.keresett = ""
        self.penznem_szuro = "Összes"
        self.megjelenites()

    @staticmethod
    def _mezo(keret, felirat, ertek=""):
        ctk.CTkLabel(keret, text=felirat, anchor="w").pack(
            fill="x", pady=(12, 4)
        )
        mezo = ctk.CTkEntry(keret)
        mezo.pack(fill="x")
        mezo.insert(0, "" if ertek is None else str(ertek))
        return mezo

    @staticmethod
    def _valaszto(keret, felirat, opciok, kijelolt=None):
        ctk.CTkLabel(keret, text=felirat, anchor="w").pack(
            fill="x", pady=(12, 4)
        )
        menu = ctk.CTkOptionMenu(keret, values=list(opciok))
        menu.pack(fill="x")
        kezdo = next(
            (nev for nev, azonosito in opciok.items() if azonosito == kijelolt),
            next(iter(opciok))
        )
        menu.set(kezdo)
        return menu

    def beszerzes_urlap(self, rekord=None):
        try:
            eszkozok, beszallitok = beszerzes_valasztok(
                rekord.EszkozID if rekord else None,
                rekord.BeszallitoID if rekord else None
            )
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba), parent=self)
            return

        if not eszkozok:
            messagebox.showwarning(
                "Hiányzó eszköz", "Előbb rögzíts egy aktív eszközt.", parent=self
            )
            return

        eszkoz_opciok = {
            f"{e.LeltariSzam} (ID: {e.EszkozID})"
            + (" – inaktív" if not e.Aktiv else ""): e.EszkozID
            for e in eszkozok
        }
        beszallito_opciok = {"Nincs megadva": None}
        for b in beszallitok:
            nev = f"{b.Nev} (ID: {b.BeszallitoID})"
            if not b.Aktiv:
                nev += " – inaktív"
            beszallito_opciok[nev] = b.BeszallitoID

        ablak = FelugroAblak(self)
        ablak.title("Beszerzés szerkesztése" if rekord else "Új beszerzés")
        ablak.geometry("780x710")
        ablak.minsize(700, 610)
        ablak.transient(self.winfo_toplevel())

        keret = ctk.CTkScrollableFrame(ablak)
        keret.pack(fill="both", expand=True, padx=20, pady=20)
        ablak.grab_set()

        eszkoz_menu = self._valaszto(
            keret, "Eszköz *", eszkoz_opciok,
            rekord.EszkozID if rekord else next(iter(eszkoz_opciok.values()))
        )
        beszallito_menu = self._valaszto(
            keret, "Beszállító (nem kötelező)", beszallito_opciok,
            rekord.BeszallitoID if rekord else None
        )
        datum = self._mezo(
            keret, "Beszerzés dátuma (ÉÉÉÉ-HH-NN)",
            rekord.BeszerzesDatuma if rekord else ""
        )
        ar = self._mezo(
            keret, "Beszerzési ár (pl. 125000 vagy 125000,50)",
            rekord.BeszerzesiAr if rekord else ""
        )
        penznem = self._mezo(
            keret, "Pénznem (pl. HUF, EUR, USD)",
            rekord.Penznem if rekord else ""
        )
        szamla = self._mezo(
            keret, "Számlaszám", rekord.SzamlaSzam if rekord else ""
        )
        megrendeles = self._mezo(
            keret, "Megrendelésszám", rekord.MegrendelesSzam if rekord else ""
        )
        ctk.CTkLabel(keret, text="Megjegyzés", anchor="w").pack(
            fill="x", pady=(12, 4)
        )
        megjegyzes = ctk.CTkTextbox(keret, height=95)
        megjegyzes.pack(fill="x")
        megjegyzes.insert("1.0", rekord.Megjegyzes or "" if rekord else "")

        def mentes():
            try:
                beszerzes_mentese(
                    rekord.BeszerzesID if rekord else None,
                    eszkoz_opciok[eszkoz_menu.get()],
                    beszallito_opciok[beszallito_menu.get()],
                    datum.get(), ar.get(), penznem.get(),
                    szamla.get(), megrendeles.get(),
                    megjegyzes.get("1.0", "end").strip()
                )
            except Exception as hiba:
                messagebox.showerror("Mentési hiba", str(hiba), parent=ablak)
                return

            ablak.destroy()
            self.megjelenites()
            messagebox.showinfo(
                "Siker", "A beszerzés adatai mentve.", parent=self
            )

        muveleti_gomb(
            keret, text="Beszerzés mentése", height=40,
            command=mentes
        ).pack(fill="x", pady=25)


from api import bekotes
bekotes(globals(), "beszerzesek")
