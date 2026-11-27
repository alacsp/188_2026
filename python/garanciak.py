from ellenorzes import szoveg as _szoveg
"""Garanciák és a hozzájuk tartozó felület kezelése."""


from ellenorzes import datum as datum_ellenorzes
from adatbazis import kapcsolat_letrehozasa, lekerdezes as _lista
from felulet_seged import FelugroAblak, muveleti_gomb
from datetime import date
from tkinter import messagebox
import customtkinter as ctk


# A garanciaműveletek lekérdezik és mentik az eszközökhöz tartozó garanciaadatokat.
def garanciak_listazasa():
    return _lista("""
        SELECT g.GaranciaID, g.EszkozID, g.GaranciaTipusID,
               e.LeltariSzam, gt.Nev AS Tipus, g.GaranciaKezdete,
               g.GaranciaVege, g.Szolgaltato, g.Megjegyzes, g.Aktiv
        FROM eszkoz.Garancia AS g
        JOIN eszkoz.Eszkoz AS e ON g.EszkozID = e.EszkozID
        LEFT JOIN torzs.GaranciaTipus AS gt
            ON g.GaranciaTipusID = gt.GaranciaTipusID
        ORDER BY g.GaranciaVege, g.GaranciaID
    """)


def garancia_valasztok(eszkoz_id=None, tipus_id=None):
    eszkozok = _lista("""
        SELECT EszkozID, LeltariSzam, Aktiv FROM eszkoz.Eszkoz
        WHERE Aktiv = 1 OR EszkozID = ? ORDER BY LeltariSzam
    """, (eszkoz_id,))
    tipusok = _lista("""
        SELECT GaranciaTipusID, Nev, Aktiv FROM torzs.GaranciaTipus
        WHERE Aktiv = 1 OR GaranciaTipusID = ? ORDER BY Nev
    """, (tipus_id,))
    return eszkozok, tipusok


def _datum(ertek, nev):
    return datum_ellenorzes(ertek, nev, kotelezo=True)



def garancia_mentese(azonosito, eszkoz_id, kezdet, vege,
                     tipus_id, szolgaltato, megjegyzes):
    if eszkoz_id is None:
        raise ValueError("Eszköz megadása kötelező.")
    kezdet = _datum(kezdet, "garancia kezdete")
    vege = _datum(vege, "garancia vége")
    if vege < kezdet:
        raise ValueError("A garancia vége nem lehet a kezdete előtt.")
    szolgaltato = _szoveg(szolgaltato, 150, "szolgáltató")
    megjegyzes = _szoveg(megjegyzes, 500, "megjegyzés")

    kapcsolat = kapcsolat_letrehozasa()
    try:
        kurzor = kapcsolat.cursor()
        from fiokok import jogosult
        jogosult(kurzor, iras=True)
        regi_eszkoz = regi_tipus = None
        if azonosito is not None:
            kurzor.execute("""
                SELECT EszkozID, GaranciaTipusID FROM eszkoz.Garancia
                WHERE GaranciaID = ? AND Aktiv = 1
            """, (azonosito,))
            regi = kurzor.fetchone()
            if regi is None:
                raise ValueError("A szerkeszthető garancia nem található.")
            regi_eszkoz, regi_tipus = regi

        if eszkoz_id != regi_eszkoz:
            kurzor.execute("""
                SELECT 1 FROM eszkoz.Eszkoz
                WHERE EszkozID = ? AND Aktiv = 1
            """, (eszkoz_id,))
            if kurzor.fetchone() is None:
                raise ValueError("A kiválasztott eszköz nem aktív.")
        if tipus_id is not None and tipus_id != regi_tipus:
            kurzor.execute("""
                SELECT 1 FROM torzs.GaranciaTipus
                WHERE GaranciaTipusID = ? AND Aktiv = 1
            """, (tipus_id,))
            if kurzor.fetchone() is None:
                raise ValueError("A garanciatípus nem aktív.")

        ertekek = (eszkoz_id, kezdet, vege, tipus_id, szolgaltato, megjegyzes)
        if azonosito is None:
            kurzor.execute("""
                INSERT INTO eszkoz.Garancia
                    (EszkozID, GaranciaKezdete, GaranciaVege,
                     GaranciaTipusID, Szolgaltato, Megjegyzes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ertekek)
        else:
            kurzor.execute("""
                UPDATE eszkoz.Garancia
                SET EszkozID = ?, GaranciaKezdete = ?, GaranciaVege = ?,
                    GaranciaTipusID = ?, Szolgaltato = ?, Megjegyzes = ?
                WHERE GaranciaID = ? AND Aktiv = 1
            """, (*ertekek, azonosito))
            if kurzor.rowcount != 1:
                raise ValueError("A garancia módosítása nem sikerült.")
        kapcsolat.commit()
    except Exception:
        kapcsolat.rollback()
        raise
    finally:
        kapcsolat.close()


def garancia_aktivitas(azonosito, aktiv):
    kapcsolat = kapcsolat_letrehozasa()
    try:
        kurzor = kapcsolat.cursor()
        from fiokok import jogosult
        jogosult(kurzor, iras=True)
        kurzor.execute("""
            UPDATE eszkoz.Garancia SET Aktiv = ?
            WHERE GaranciaID = ? AND Aktiv <> ?
        """, (int(aktiv), azonosito, int(aktiv)))
        if kurzor.rowcount != 1:
            raise ValueError("A garancia nem található, vagy már ebben az állapotban van.")
        kapcsolat.commit()
    except Exception:
        kapcsolat.rollback()
        raise
    finally:
        kapcsolat.close()



# A garanciaképernyő szűri a rekordokat és kezeli a garanciaűrlapokat.
class GaranciakFelulet(ctk.CTkFrame):
    def __init__(self, szulo):
        super().__init__(szulo, fg_color="transparent")
        self.keresett = ""
        self.nezet = "Aktív"
        self.megjelenites()

    def nezet_valtas(self, ertek):
        self.nezet = ertek
        self.megjelenites()

    def megjelenites(self):
        for elem in self.winfo_children():
            elem.destroy()
        try:
            adatok = garanciak_listazasa()
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba), parent=self)
            return

        vezerlok = ctk.CTkFrame(self, fg_color="transparent")
        vezerlok.pack(fill="x", padx=10, pady=10)
        muveleti_gomb(vezerlok, text="+ Új garancia", width=135,
                      command=self.urlap).pack(side="left", padx=5)
        valto = ctk.CTkSegmentedButton(vezerlok, values=["Aktív", "Inaktív"],
                                       command=self.nezet_valtas)
        valto.pack(side="left", padx=12)
        valto.set(self.nezet)
        kereso = ctk.CTkEntry(vezerlok, width=195, placeholder_text="Keresés...")
        kereso.pack(side="left", padx=5)
        kereso.insert(0, self.keresett)

        def kereses():
            self.keresett = kereso.get().strip()
            self.megjelenites()

        ctk.CTkButton(vezerlok, text="Keresés", width=78,
                      command=kereses).pack(side="left", padx=4)
        kereso.bind("<Return>", lambda _e: kereses())
        ctk.CTkButton(vezerlok, text="Alaphelyzet", width=95,
                      command=self.alaphelyzet).pack(side="left", padx=4)

        sorok = [r for r in adatok if bool(r.Aktiv) == (self.nezet == "Aktív")]
        if self.keresett:
            keresett = self.keresett.casefold()
            sorok = [r for r in sorok if any(keresett in str(v or "").casefold()
                    for v in (r.LeltariSzam, r.Tipus, r.Szolgaltato, r.Megjegyzes))]
        ctk.CTkLabel(self, text=f"Garanciák: {len(sorok)} / {len(adatok)}",
                     anchor="w").pack(fill="x", padx=15, pady=5)
        tabla = ctk.CTkScrollableFrame(self)
        tabla.pack(fill="both", expand=True, padx=10, pady=5)
        fejlecek = ("Eszköz", "Típus", "Kezdete", "Vége", "Állapot", "Műveletek")
        szelessegek = (125, 165, 105, 105, 115, 205)
        for oszlop, nev in enumerate(fejlecek):
            ctk.CTkLabel(tabla, text=nev, width=szelessegek[oszlop], anchor="w",
                         font=ctk.CTkFont(weight="bold")
                         ).grid(row=0, column=oszlop, padx=5, pady=8, sticky="w")

        ma = date.today()
        for index, rekord in enumerate(sorok, start=1):
            allapot = ("Inaktív" if not rekord.Aktiv else
                       "Még nem kezdődött" if rekord.GaranciaKezdete > ma else
                       "Lejárt" if rekord.GaranciaVege < ma else "Érvényes")
            ertekek = (rekord.LeltariSzam, rekord.Tipus or "–",
                       rekord.GaranciaKezdete, rekord.GaranciaVege, allapot)
            for oszlop, ertek in enumerate(ertekek):
                ctk.CTkLabel(tabla, text=str(ertek), width=szelessegek[oszlop],
                             anchor="w", wraplength=szelessegek[oszlop]
                             ).grid(row=index, column=oszlop, padx=5, pady=5, sticky="w")
            gombok = ctk.CTkFrame(tabla, fg_color="transparent")
            gombok.grid(row=index, column=5, padx=5)
            if rekord.Aktiv:
                muveleti_gomb(gombok, text="Szerkesztés", width=93,
                              command=lambda r=rekord: self.urlap(r)
                              ).pack(side="left", padx=2)
            muveleti_gomb(
                gombok, text="Inaktiválás" if rekord.Aktiv else "Visszaállítás",
                width=102, command=lambda r=rekord: self.aktivitas(r)
            ).pack(side="left", padx=2)
        if not sorok:
            ctk.CTkLabel(tabla, text="Nincs megjeleníthető garancia.").grid(
                row=1, column=0, columnspan=6, pady=25)

    def alaphelyzet(self):
        self.keresett = ""
        self.megjelenites()

    def aktivitas(self, rekord):
        aktiv = not bool(rekord.Aktiv)
        muvelet = "visszaállítod" if aktiv else "inaktiválod"
        if not messagebox.askyesno("Megerősítés",
                                   f"Biztosan {muvelet} ezt a garanciát?",
                                   parent=self):
            return
        try:
            garancia_aktivitas(rekord.GaranciaID, aktiv)
            self.megjelenites()
        except Exception as hiba:
            messagebox.showerror("Hiba", str(hiba), parent=self)

    @staticmethod
    def mezo(keret, felirat, ertek=""):
        ctk.CTkLabel(keret, text=felirat, anchor="w").pack(fill="x", pady=(12, 3))
        mezo = ctk.CTkEntry(keret)
        mezo.pack(fill="x")
        mezo.insert(0, str("" if ertek is None else ertek))
        return mezo

    @staticmethod
    def valaszto(keret, felirat, opciok, azonosito=None):
        ctk.CTkLabel(keret, text=felirat, anchor="w").pack(fill="x", pady=(12, 3))
        menu = ctk.CTkOptionMenu(keret, values=list(opciok))
        menu.pack(fill="x")
        menu.set(next((n for n, az in opciok.items() if az == azonosito),
                      next(iter(opciok))))
        return menu

    def urlap(self, rekord=None):
        try:
            eszkozok, tipusok = garancia_valasztok(
                rekord.EszkozID if rekord else None,
                rekord.GaranciaTipusID if rekord else None)
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba), parent=self)
            return
        if not eszkozok:
            messagebox.showwarning("Hiányzó adat", "Előbb vegyél fel egy eszközt.", parent=self)
            return
        eszkoz_opciok = {f"{e.LeltariSzam} (ID: {e.EszkozID})": e.EszkozID
                         for e in eszkozok}
        tipus_opciok = {"Nincs megadva": None}
        tipus_opciok.update({f"{t.Nev} (ID: {t.GaranciaTipusID})": t.GaranciaTipusID
                             for t in tipusok})
        ablak = FelugroAblak(self)
        ablak.title("Garancia szerkesztése" if rekord else "Új garancia")
        ablak.geometry("740x680")
        ablak.minsize(670, 570)
        ablak.transient(self.winfo_toplevel())
        keret = ctk.CTkScrollableFrame(ablak)
        keret.pack(fill="both", expand=True, padx=20, pady=20)
        ablak.grab_set()
        eszkoz = self.valaszto(keret, "Eszköz *", eszkoz_opciok,
                              rekord.EszkozID if rekord else None)
        kezdet = self.mezo(keret, "Garancia kezdete * (ÉÉÉÉ-HH-NN)",
                           rekord.GaranciaKezdete if rekord else "")
        vege = self.mezo(keret, "Garancia vége * (ÉÉÉÉ-HH-NN)",
                         rekord.GaranciaVege if rekord else "")
        tipus = self.valaszto(keret, "Garanciatípus", tipus_opciok,
                             rekord.GaranciaTipusID if rekord else None)
        szolgaltato = self.mezo(keret, "Szolgáltató",
                                rekord.Szolgaltato if rekord else "")
        ctk.CTkLabel(keret, text="Megjegyzés", anchor="w").pack(
            fill="x", pady=(12, 3))
        megjegyzes = ctk.CTkTextbox(keret, height=85)
        megjegyzes.pack(fill="x")
        megjegyzes.insert("1.0", (rekord.Megjegyzes or "") if rekord else "")

        def mentes():
            try:
                garancia_mentese(
                    rekord.GaranciaID if rekord else None,
                    eszkoz_opciok[eszkoz.get()], kezdet.get(), vege.get(),
                    tipus_opciok[tipus.get()], szolgaltato.get(),
                    megjegyzes.get("1.0", "end").strip())
            except Exception as hiba:
                messagebox.showerror("Mentési hiba", str(hiba), parent=ablak)
                return
            ablak.destroy()
            self.megjelenites()
            messagebox.showinfo("Siker", "A garancia mentve.", parent=self)

        muveleti_gomb(keret, text="Mentés", height=40,
                      command=mentes).pack(fill="x", pady=20)


from api import bekotes
bekotes(globals(), "garanciak")
