"""A főablak és az alkalmazás indítása."""


from felulet_seged import FelugroAblak, muveleti_gomb
from tkinter import messagebox
import fiokok
from fiokok import Belepes, FiokFelulet, idozitok_leallitasa
from torzsadatok import TorzsadatFelulet
from infrastruktura import InfrastrukturaFelulet
from partnerek import PartnerekFelulet
from beszerzesek import BeszerzesekFelulet
from garanciak import GaranciakFelulet
from karbantartasok import KarbantartasokFelulet
from halozat import HalozatFelulet
from eszkozok import (
    eszkozok_lekerdezese,
    torzsadatok_lekerdezese,
    eszkoz_rogzitese,
    eszkoz_adatainak_lekerdezese,
    eszkoz_modositasa,
    eszkoz_inaktivalasa,
    eszkoz_visszaallitasa,
    helyek_lekerdezese,
    eszkoz_helyenek_modositasa,
)
import customtkinter as ctk



ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
ctk.ThemeManager.theme["CTkButton"]["corner_radius"] = 14


# A főablak kezeli a felhasználói munkamenetet, az oldalak közötti navigációt és az eszköznézetet.
class EszkozNyilvantartas(ctk.CTk):
    def destroy(self):
        idozitok_leallitasa(self)
        super().destroy()

    def __init__(self):
        super().__init__()
        self.felhasznalo = fiokok.aktualis()
        self.title(f"Eszköznyilvántartó rendszer – {self.felhasznalo.Nev}")
        self.geometry("1300x720")
        self.minsize(1150, 650)


        
        self.menu_nyitva = True

        self.menu = ctk.CTkFrame(
            self, width=220, corner_radius=0
        )
        self.menu.pack(side="left", fill="y")
        self.menu.pack_propagate(False)

        self.menu_gomb = ctk.CTkButton(
            self.menu,
            text="☰  Menü",
            width=190,
            height=42,
            corner_radius=14,
            command=self.menu_valtas
        )
        self.menu_gomb.pack(padx=10, pady=(15, 10), fill="x")

        
        self.menu_tartalom = ctk.CTkScrollableFrame(
            self.menu, fg_color="transparent"
        )
        self.menu_tartalom.pack(fill="both", expand=True)

        ctk.CTkLabel(
            self.menu_tartalom,
            text="Eszköznyilvántartás",
            font=ctk.CTkFont(size=19, weight="bold")
        ).pack(padx=10, pady=(15, 25))

        oldalak = [
            "Főoldal",
            "Eszközök",
            "Infrastruktúra",
            "Partnerek",
            "Beszerzések",
            "Garanciák",
            "Karbantartások",
            "Hálózat"
        ]

        oldalak += ["Saját fiók"]
        oldalak += ["Törzsadatok"]

        for oldal in oldalak:
            ctk.CTkButton(
                self.menu_tartalom,
                text=oldal,
                height=42,
                corner_radius=14,
                command=lambda nev=oldal: self.oldal_megjelenitese(nev)
            ).pack(padx=12, pady=5, fill="x")

        ctk.CTkButton(self.menu_tartalom, text="Kijelentkezés", command=self.kijelentkezes).pack(padx=12, pady=8, fill="x")
        self.after(30000, self.munkamenet_ellenorzese)

        self.tartalom = ctk.CTkFrame(self, corner_radius=0)
        self.tartalom.pack(side="right", fill="both", expand=True)
        self.kereses = ctk.StringVar()
        self.statusz_szuro = ctk.StringVar(value="Összes")
        self.aktiv_nezet = True
        self.nezet_valtozo = ctk.StringVar(value="Aktív")
        self.oldal_megjelenitese("Főoldal")
        self.after(300, lambda: self.state("zoomed"))

    def kijelentkezes(self):
        fiokok.kilepes()
        self.destroy()

    # A rendszeres ellenőrzés lejárt munkamenet vagy adatbázishiba esetén kijelentkeztet.
    def munkamenet_ellenorzese(self):
        try:
            fiokok.aktualis()
        except Exception:
            messagebox.showwarning("Új bejelentkezés szükséges", "A munkamenet vagy az adatbáziskapcsolat megszűnt.", parent=self)
            self.kijelentkezes()
            return
        self.after(30000, self.munkamenet_ellenorzese)

    def menu_valtas(self):
        """Oldalsó menü kinyitása és becsukása."""

        self.menu_nyitva = not self.menu_nyitva

        if self.menu_nyitva:
            self.menu.configure(width=220)
            self.menu_gomb.configure(
                text="☰  Menü",
                width=190
            )
            self.menu_tartalom.pack(
                fill="both", expand=True
            )
        else:
            self.menu_tartalom.pack_forget()
            self.menu.configure(width=58)
            self.menu_gomb.configure(
                text="☰",
                width=38
            )

    # Az oldalkiválasztás a megfelelő modul felületét tölti be a fő tartalomterületre.
    def oldal_megjelenitese(self, oldal):
        for elem in self.tartalom.winfo_children():
            elem.destroy()

        ctk.CTkLabel(
            self.tartalom,
            text=oldal,
            font=ctk.CTkFont(size=28, weight="bold")
        ).pack(padx=30, pady=(40, 20), anchor="w")

        if oldal == "Saját fiók":
            FiokFelulet(self.tartalom).pack(fill="both", expand=True, padx=20, pady=20)
            return
        if oldal == "Törzsadatok":
            TorzsadatFelulet(self.tartalom).pack(fill="both", expand=True, padx=20, pady=20)
            return
        if oldal == "Főoldal":
            self.fooldal_megjelenitese()

        elif oldal == "Eszközök":
            self.eszkozok_megjelenitese()
        else:
            feluletek = {
                "Infrastruktúra": InfrastrukturaFelulet,
                "Partnerek": PartnerekFelulet,
                "Beszerzések": BeszerzesekFelulet,
                "Garanciák": GaranciakFelulet,
                "Karbantartások": KarbantartasokFelulet,
                "Hálózat": HalozatFelulet,
            }
            felulet = feluletek.get(oldal)
            if felulet is not None:
                felulet(self.tartalom).pack(
                    fill="both", expand=True, padx=20, pady=(0, 20)
                )
            else:
                ctk.CTkLabel(
                    self.tartalom, text=f"{oldal} modul – fejlesztés alatt"
                ).pack(padx=30, anchor="w")


    def nezet_valtas(self, ertek):
        self.aktiv_nezet = (ertek == "Aktív")
        self.kereses.set("")
        self.statusz_szuro.set("Összes")
        self.oldal_megjelenitese("Eszközök")

    # A főoldal összesítő kártyákat és gyors elérési lehetőségeket jelenít meg.
    def fooldal_megjelenitese(self):
        """A főoldal statisztikáinak és gyorsgombjainak megjelenítése."""

        tartalom = ctk.CTkScrollableFrame(
            self.tartalom, fg_color="transparent"
        )
        tartalom.pack(
            fill="both", expand=True, padx=24, pady=(0, 20)
        )

        
        fejlec = ctk.CTkFrame(tartalom, fg_color="transparent")
        fejlec.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            fejlec,
            text="Az IT-infrastruktúra aktuális állapota",
            font=ctk.CTkFont(size=16)
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            fejlec,
            text="Frissítés",
            width=110,
            command=lambda: self.oldal_megjelenitese("Főoldal")
        ).pack(side="right", padx=8)

        
        try:
            from eszkozok import fooldal_statisztika
            adat = fooldal_statisztika()
        except Exception as hiba:
            adat = None
            ctk.CTkLabel(
                tartalom,
                text=f"A statisztikák nem tölthetők be: {hiba}",
                text_color="#E57373",
                wraplength=850
            ).pack(anchor="w", padx=8, pady=10)

        
        statisztikak = [
            ("Aktív eszközök", adat.AktivEszkoz if adat else "—"),
            ("Üzemben", adat.Uzemben if adat else "—"),
            ("Hibás eszközök", adat.Hibas if adat else "—"),
            ("Karbantartás alatt", adat.Karbantartas if adat else "—"),
            ("Aktív telephelyek", adat.Telephely if adat else "—"),
            ("Lejáró garanciák (30 nap)",
             adat.LejaroGarancia if adat else "—")
        ]

        kartyak = ctk.CTkFrame(tartalom, fg_color="transparent")
        kartyak.pack(fill="x")

        for oszlop in range(3):
            kartyak.grid_columnconfigure(
                oszlop, weight=1, uniform="statisztika"
            )

        for i, (felirat, ertek) in enumerate(statisztikak):
            kartya = ctk.CTkFrame(kartyak, corner_radius=18)
            kartya.grid(
                row=i // 3,
                column=i % 3,
                padx=8,
                pady=8,
                sticky="nsew"
            )

            ctk.CTkLabel(
                kartya,
                text=felirat,
                font=ctk.CTkFont(size=14),
                anchor="w"
            ).pack(fill="x", padx=20, pady=(18, 4))

            ctk.CTkLabel(
                kartya,
                text=str(ertek),
                font=ctk.CTkFont(size=34, weight="bold"),
                anchor="w"
            ).pack(fill="x", padx=20, pady=(0, 18))

        
        ctk.CTkLabel(
            tartalom,
            text="Gyorselérés",
            font=ctk.CTkFont(size=21, weight="bold")
        ).pack(anchor="w", padx=8, pady=(25, 10))

        gyorsgombok = ctk.CTkFrame(
            tartalom, fg_color="transparent"
        )
        gyorsgombok.pack(fill="x")

        for oszlop in range(4):
            gyorsgombok.grid_columnconfigure(
                oszlop, weight=1, uniform="gyorsgomb"
            )

        oldalak = [
            "Új eszköz", "Eszközök",
            "Infrastruktúra", "Partnerek",
            "Beszerzések", "Garanciák",
            "Karbantartások", "Hálózat"
        ]

        for i, oldal in enumerate(oldalak):
            if oldal == "Új eszköz" and self.felhasznalo.Megtekinto:
                continue
            if oldal == "Új eszköz":
                muvelet = self.eszkoz_urlap
            else:
                muvelet = lambda nev=oldal: self.oldal_megjelenitese(nev)

            ctk.CTkButton(
                gyorsgombok,
                text=oldal,
                height=46,
                command=muvelet
            ).grid(
                row=i // 4,
                column=i % 4,
                padx=8,
                pady=8,
                sticky="ew"
            )

    # Az eszköznézet kezeli a keresést, a szűrést, a helymódosítást és az adatlapot.
    def eszkozok_megjelenitese(self):
        valto = ctk.CTkSegmentedButton(
            self.tartalom,
            values=["Aktív", "Inaktív"],
            variable=self.nezet_valtozo,
            command=self.nezet_valtas
        )
        valto.pack(padx=30, pady=10, anchor="w")

        if self.aktiv_nezet:
            muveleti_gomb(
                self.tartalom,
                text="+ Új eszköz",
                width=160,
                command=self.eszkoz_urlap
            ).pack(padx=30, pady=10, anchor="w")

        try:
            eszkozok = eszkozok_lekerdezese(aktiv=self.aktiv_nezet)
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba))
            return

        osszes = len(eszkozok)

        szurokeret = ctk.CTkFrame(self.tartalom)
        szurokeret.pack(fill="x", padx=30, pady=10)

        kereso = ctk.CTkEntry(
            szurokeret,
            textvariable=self.kereses,
            placeholder_text="Eszköz keresése...",
            width=230
        )
        kereso.pack(side="left", padx=5)

        statusz_valaszto = ctk.CTkOptionMenu(
            szurokeret,
            values=["Összes"] + sorted({e.Statusz for e in eszkozok}),
            variable=self.statusz_szuro,
            width=140
        )
        statusz_valaszto.pack(side="left", padx=5)


        def frissites():
            self.oldal_megjelenitese("Eszközök")


        def alaphelyzet():
            self.kereses.set("")
            self.statusz_szuro.set("Összes")
            frissites()


        ctk.CTkButton(
            szurokeret,
            text="Keresés",
            width=100,
            command=frissites
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            szurokeret,
            text="Alaphelyzet",
            width=100,
            command=alaphelyzet
        ).pack(side="left", padx=5)

        kereso.bind("<Return>", lambda event: frissites())

        
        szoveg = self.kereses.get().strip().casefold()
        statusz = self.statusz_szuro.get()

        eszkozok = [
            e for e in eszkozok
            if (statusz == "Összes" or e.Statusz == statusz)
            and (
                not szoveg
                or any(
                    szoveg in str(adat).casefold()
                    for adat in (
                        e.LeltariSzam,
                        e.Gyarto,
                        e.Modell,
                        e.Statusz,
                        e.Hely or ""
                    )
                )
            )
        ]

        ctk.CTkLabel(
            self.tartalom,
            text=f"{'Aktív' if self.aktiv_nezet else 'Inaktív'} eszközök – "
                f"Találatok: {len(eszkozok)} / {osszes}"
        ).pack(padx=30, pady=10, anchor="w")

        tabla = ctk.CTkScrollableFrame(self.tartalom)
        tabla.pack(fill="both", expand=True, padx=30, pady=20)

        fejlecek = ["Leltári szám", "Gyártó", "Modell", "Státusz", "Hely", "Műveletek"]
        for oszlop, nev in enumerate(fejlecek):
            ctk.CTkLabel(tabla, text=nev, width=130, anchor="w",
                         font=ctk.CTkFont(weight="bold")
                         ).grid(row=0, column=oszlop, padx=8, pady=10, sticky="w")

        if not eszkozok:
            ctk.CTkLabel(tabla, text="Nincs a keresésnek megfelelő eszköz."
                         ).grid(row=1, column=0, columnspan=6, pady=25)
            return

        for sor, eszkoz in enumerate(eszkozok, start=1):
            adatok = [eszkoz.LeltariSzam, eszkoz.Gyarto, eszkoz.Modell,
                      eszkoz.Statusz, eszkoz.Hely or "Nincs megadva"]
            for oszlop, ertek in enumerate(adatok):
                ctk.CTkLabel(tabla, text=str(ertek), width=130, anchor="w"
                             ).grid(row=sor, column=oszlop, padx=8, pady=5, sticky="w")

            gombok = ctk.CTkFrame(tabla, fg_color="transparent")
            gombok.grid(row=sor, column=5, padx=5, pady=5)

            if self.aktiv_nezet:
                muveleti_gomb(
                    gombok,
                    text="Szerkesztés",
                    width=95,
                    command=lambda az=eszkoz.EszkozID:
                        self.eszkoz_urlap(az)
                ).pack(side="left", padx=3)

                muveleti_gomb(
                    gombok,
                    text="Hely",
                    width=65,
                    command=lambda az=eszkoz.EszkozID:
                        self.hely_modositasa(az)
                ).pack(side="left", padx=3)

                muveleti_gomb(
                    gombok,
                    text="Inaktiválás",
                    width=95,
                    fg_color="#B33A3A",
                    hover_color="#902E2E",
                    command=lambda az=eszkoz.EszkozID, leltari=eszkoz.LeltariSzam:
                        self.inaktivalas_megerositese(az, leltari)
                ).pack(side="left", padx=3)

            else:
                muveleti_gomb(
                    gombok,
                    text="Visszaállítás",
                    width=110,
                    command=lambda az=eszkoz.EszkozID, leltari=eszkoz.LeltariSzam:
                        self.visszaallitas_megerositese(az, leltari)
                ).pack(side="left", padx=3)

    def inaktivalas_megerositese(self, eszkoz_id, leltari_szam):
        valasz = messagebox.askyesno(
            "Inaktiválás",
            f"Biztosan inaktiválod ezt az eszközt?\n\n"
            f"Leltári szám: {leltari_szam}",
            parent=self
        )

        if not valasz:
            return

        try:
            eszkoz_inaktivalasa(eszkoz_id)
        except Exception as hiba:
            messagebox.showerror("Hiba", str(hiba), parent=self)
            return

        self.oldal_megjelenitese("Eszközök")
        messagebox.showinfo(
            "Sikeres inaktiválás",
            "Az eszköz inaktiválása megtörtént.",
            parent=self
    )

    def visszaallitas_megerositese(self, eszkoz_id, leltari_szam):
        if not messagebox.askyesno(
            "Visszaállítás",
            f"Visszaállítod az eszközt?\n\nLeltári szám: {leltari_szam}",
            parent=self
        ):
            return

        try:
            eszkoz_visszaallitasa(eszkoz_id)
        except Exception as hiba:
            messagebox.showerror("Hiba", str(hiba), parent=self)
            return

        self.oldal_megjelenitese("Eszközök")
        messagebox.showinfo(
            "Visszaállítva",
            "Az eszköz újra aktív. A rackpozíciót szükség esetén add meg újra.",
            parent=self
    )

    def hely_modositasa(self, eszkoz_id):
        try:
            eszkoz = eszkoz_adatainak_lekerdezese(eszkoz_id)
            helyek = helyek_lekerdezese()
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba), parent=self)
            return

        if eszkoz is None:
            messagebox.showwarning(
                "Nem található", "Az eszköz nem található.", parent=self
            )
            return

        opciok = {"Nincs megadva": None}
        for hely in helyek:
            nev = f"{hely.Telephely} / {hely.Terem or '—'} / {hely.Hely}"
            if hely.HelyTipus == "RACK":
                nev += f" (rack: {hely.RackMagassag or '?'} U)"
            nev += f" [ID: {hely.HelyID}]"
            opciok[nev] = hely.HelyID

        ablak = FelugroAblak(self)
        ablak.title(f"Eszköz elhelyezése – {eszkoz.LeltariSzam}")
        ablak.geometry("720x450")
        ablak.minsize(650, 400)
        ablak.transient(self)
        ablak.grab_set()

        keret = ctk.CTkFrame(ablak)
        keret.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            keret, text="Telephely / Terem / Hely", anchor="w"
        ).pack(fill="x", pady=(12, 5))

        helymenu = ctk.CTkOptionMenu(
            keret, values=list(opciok), width=610
        )
        helymenu.pack(fill="x")

        if eszkoz.HelyID is not None and eszkoz.HelyID not in opciok.values():
            opciok[f"Jelenlegi, inaktív hely (ID: {eszkoz.HelyID})"] = eszkoz.HelyID
            helymenu.configure(values=list(opciok))

        kezdo = next(
            (nev for nev, az in opciok.items() if az == eszkoz.HelyID),
            "Nincs megadva"
        )
        helymenu.set(kezdo)

        ctk.CTkLabel(
            keret, text="Rackpozíció kezdete (U)", anchor="w"
        ).pack(fill="x", pady=(15, 5))

        poziciomezo = ctk.CTkEntry(
            keret, placeholder_text="Pl. 12 – csak rackhez"
        )
        poziciomezo.pack(fill="x")

        if eszkoz.RackPozicioKezdet is not None:
            poziciomezo.insert(0, str(eszkoz.RackPozicioKezdet))

        ctk.CTkLabel(
            keret,
            text="Rack esetén add meg az U-pozíciót; más típusú "
                "hely esetén hagyd üresen.",
            wraplength=610
        ).pack(pady=15)

        def mentes():
            szoveg = poziciomezo.get().strip()

            try:
                pozicio = int(szoveg) if szoveg else None
            except ValueError:
                messagebox.showwarning(
                    "Hibás pozíció",
                    "Egész számot adj meg.",
                    parent=ablak
                )
                return

            try:
                eszkoz_helyenek_modositasa(
                    eszkoz_id,
                    opciok[helymenu.get()],
                    pozicio
                )
            except Exception as hiba:
                messagebox.showerror(
                    "Mentési hiba",
                    str(hiba),
                    parent=ablak
                )
                return

            ablak.destroy()
            self.oldal_megjelenitese("Eszközök")
            messagebox.showinfo(
                "Siker",
                "Az eszköz helye mentve.",
                parent=self
            )

        muveleti_gomb(
            keret,
            text="Hely mentése",
            height=40,
            command=mentes
        ).pack(fill="x", pady=10)
    
    def eszkoz_urlap(self, eszkoz_id=None):
        """Közös ablak új eszköz felvételéhez és meglévő szerkesztéséhez."""
        try:
            eszkoz = (eszkoz_adatainak_lekerdezese(eszkoz_id)
                      if eszkoz_id is not None else None)
            modellek, statuszok = torzsadatok_lekerdezese(
                eszkoz.ModellID if eszkoz else None,
                eszkoz.StatuszID if eszkoz else None)
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba))
            return

        if eszkoz_id is not None and eszkoz is None:
            messagebox.showwarning("Nem található", "A kiválasztott eszköz nem található.")
            return
        if not modellek or not statuszok:
            messagebox.showwarning("Hiányzó törzsadat", "Nincs választható modell vagy státusz.")
            return

        modell_opciok = {
            f"{m.Gyarto} – {m.Modell} (ID: {m.ModellID})"
            + (" – inaktív" if not m.Aktiv else ""): m.ModellID
            for m in modellek
        }
        statusz_opciok = {
            f"{s.Nev} (ID: {s.StatuszID})" + (" – inaktív" if not s.Aktiv else ""): s.StatuszID
            for s in statuszok
        }

        szerkesztes = eszkoz_id is not None
        cim = "Eszköz szerkesztése" if szerkesztes else "Új eszköz felvétele"
        ablak = FelugroAblak(self)
        ablak.title(cim)
        ablak.geometry("720x700")
        ablak.minsize(650, 620)
        ablak.transient(self)
        ablak.grab_set()

        keret = ctk.CTkScrollableFrame(ablak)
        keret.pack(fill="both", expand=True, padx=20, pady=20)

        def felirat(szoveg):
            ctk.CTkLabel(keret, text=szoveg, anchor="w"
                         ).pack(fill="x", pady=(12, 4))

        def szovegmezo(cimke, kezdoertek=""):
            felirat(cimke)
            mezo = ctk.CTkEntry(keret)
            mezo.pack(fill="x")
            mezo.insert(0, kezdoertek or "")
            return mezo

        def valaszto(cimke, opciok, kijelolt_id=None):
            felirat(cimke)
            menu = ctk.CTkOptionMenu(keret, values=list(opciok))
            menu.pack(fill="x")
            kijelolt = next((nev for nev, az in opciok.items() if az == kijelolt_id),
                            next(iter(opciok)))
            menu.set(kijelolt)
            return menu

        leltari = szovegmezo("Leltári szám *", eszkoz.LeltariSzam if eszkoz else "")
        sorozat = szovegmezo("Sorozatszám", eszkoz.Sorozatszam if eszkoz else "")
        modell = valaszto("Gyártó és modell *", modell_opciok,
                          eszkoz.ModellID if eszkoz else None)
        statusz = valaszto("Státusz *", statusz_opciok,
                           eszkoz.StatuszID if eszkoz else None)
        datum_mezo = szovegmezo("Üzembe helyezés dátuma (ÉÉÉÉ-HH-NN, üresen törölhető)",
                                str(eszkoz.UzembehelyezesDatuma) if eszkoz and eszkoz.UzembehelyezesDatuma else "")
        felirat("Megjegyzés")
        megjegyzes = ctk.CTkTextbox(keret, height=100)
        megjegyzes.pack(fill="x")
        if eszkoz:
            megjegyzes.insert("1.0", eszkoz.Megjegyzes or "")

        def mentes():
            leltari_szam = leltari.get().strip()
            if not leltari_szam:
                messagebox.showwarning("Hiányzó adat", "A leltári szám kötelező.", parent=ablak)
                return

            adatok = (leltari_szam, sorozat.get().strip(),
                      modell_opciok[modell.get()], statusz_opciok[statusz.get()],
                      megjegyzes.get("1.0", "end").strip())
            try:
                if szerkesztes:
                    eszkoz_modositasa(eszkoz_id, *adatok, uzembehelyezes=datum_mezo.get())
                else:
                    eszkoz_rogzitese(*adatok, uzembehelyezes=datum_mezo.get().strip() or "auto")
                    self.aktiv_nezet = True
                    self.nezet_valtozo.set("Aktív")
                    self.kereses.set("")
                    self.statusz_szuro.set("Összes")
            except Exception as hiba:
                messagebox.showerror("Mentési hiba", str(hiba), parent=ablak)
                return

            ablak.destroy()
            self.oldal_megjelenitese("Eszközök")
            messagebox.showinfo("Sikeres mentés", "Az eszköz adatai mentve.", parent=self)

        gomb_felirat = "Módosítások mentése" if szerkesztes else "Eszköz mentése"
        muveleti_gomb(keret, text=gomb_felirat, height=40,
                      command=mentes).pack(fill="x", pady=25)


if __name__ == "__main__":
    while True:
        belepes = Belepes()
        belepes.mainloop()
        if not belepes.siker:
            break
        alkalmazas = EszkozNyilvantartas()
        alkalmazas.mainloop()
        fiokok.kilepes()
