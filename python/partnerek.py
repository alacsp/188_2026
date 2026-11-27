"""Ügyfelek, beszállítók és kapcsolataik kezelése."""


from datetime import date
from adatbazis import kapcsolat_letrehozasa, lekerdezes as _lekerdezes, tranzakcio as _tranzakcio
from felulet_seged import FelugroAblak, muveleti_gomb
from tkinter import messagebox
import customtkinter as ctk


PARTNERTABLAK = {
    "Ügyfelek": ("partner.Ugyfel", "UgyfelID"),
    "Beszállítók": ("partner.Beszallito", "BeszallitoID"),
}


def _datum(ertek, kotelezo=False):
    """YYYY-MM-DD szövegből DATE; üres érték esetén None."""
    if isinstance(ertek, date):
        return ertek
    if not ertek or not str(ertek).strip():
        if kotelezo:
            raise ValueError("A kezdődátum megadása kötelező.")
        return None
    try:
        return date.fromisoformat(str(ertek).strip())
    except ValueError as hiba:
        raise ValueError("A dátum formátuma ÉÉÉÉ-HH-NN legyen.") from hiba


def _rovidites(ertek, hossz, mezonev, kotelezo=False):
    szoveg = (ertek or "").strip()
    if kotelezo and not szoveg:
        raise ValueError(f"A(z) {mezonev} megadása kötelező.")
    if len(szoveg) > hossz:
        raise ValueError(f"A(z) {mezonev} legfeljebb {hossz} karakter lehet.")
    return szoveg or None


# A partnerfüggvények ügyfeleket, beszállítókat és az eszközkapcsolatokat kezelik.
def partnerek_listazasa(tipus, aktiv=True):
    if tipus not in PARTNERTABLAK:
        raise ValueError("Ismeretlen partnernézet.")
    tabla, azonosito = PARTNERTABLAK[tipus]
    if tipus == "Ügyfelek":
        kapcsolat_szam = """
            (SELECT COUNT(*) FROM partner.EszkozUgyfelKapcsolat k
             WHERE k.UgyfelID = p.UgyfelID
               AND k.ErvenyesTol <= CAST(GETDATE() AS date)
               AND (k.ErvenyesIg IS NULL OR k.ErvenyesIg >= CAST(GETDATE() AS date)))
        """
    else:
        kapcsolat_szam = """
            (SELECT COUNT(*) FROM eszkoz.Beszerzes b
             WHERE b.BeszallitoID = p.BeszallitoID)
        """
    return _lekerdezes(f"""
        SELECT p.{azonosito} AS Azonosito, p.Nev, p.Adoszam,
               p.KapcsolattartoNev, p.KapcsolattartoEmail,
               p.KapcsolattartoTelefon, p.Megjegyzes, p.Aktiv,
               {kapcsolat_szam} AS Hivatkozasok
        FROM {tabla} p
        WHERE p.Aktiv = ?
        ORDER BY p.Nev
    """, (int(aktiv),))


def partner_mentese(tipus, azonosito, nev, adoszam, kapcsolattarto,
                    email, telefon, megjegyzes):
    if tipus not in PARTNERTABLAK:
        raise ValueError("Ismeretlen partnernézet.")
    tabla, kulcs = PARTNERTABLAK[tipus]
    ertekek = (
        _rovidites(nev, 200, "név", kotelezo=True),
        _rovidites(adoszam, 50, "adószám"),
        _rovidites(kapcsolattarto, 150, "kapcsolattartó"),
        _rovidites(email, 150, "e-mail-cím"),
        _rovidites(telefon, 50, "telefonszám"),
        _rovidites(megjegyzes, 500, "megjegyzés"),
    )
    if ertekek[3] and ("@" not in ertekek[3] or " " in ertekek[3]):
        raise ValueError("A kapcsolattartó e-mail-címe hibásnak tűnik.")

    def mentes(k):
        if azonosito is None:
            k.execute(f"""
                INSERT INTO {tabla}
                    (Nev, Adoszam, KapcsolattartoNev,
                     KapcsolattartoEmail, KapcsolattartoTelefon, Megjegyzes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ertekek)
        else:
            k.execute(f"""
                UPDATE {tabla}
                SET Nev = ?, Adoszam = ?, KapcsolattartoNev = ?,
                    KapcsolattartoEmail = ?, KapcsolattartoTelefon = ?, Megjegyzes = ?
                WHERE {kulcs} = ? AND Aktiv = 1
            """, (*ertekek, azonosito))
            if k.rowcount != 1:
                raise ValueError("A módosítandó aktív partner nem található.")

    _tranzakcio(mentes)


def partner_aktivitas(tipus, azonosito, aktiv):
    if tipus not in PARTNERTABLAK:
        raise ValueError("Ismeretlen partnernézet.")
    tabla, kulcs = PARTNERTABLAK[tipus]

    def mentes(k):
        k.execute(f"""
            SELECT Aktiv FROM {tabla} WITH (UPDLOCK, HOLDLOCK)
            WHERE {kulcs} = ?
        """, (azonosito,))
        sor = k.fetchone()
        if sor is None or bool(sor.Aktiv) == bool(aktiv):
            raise ValueError("A partner nem található, vagy már ebben az állapotban van.")

        if tipus == "Ügyfelek" and not aktiv:
            k.execute("""
                SELECT COUNT(*) FROM partner.EszkozUgyfelKapcsolat
                WHERE UgyfelID = ?
                  AND (ErvenyesIg IS NULL OR ErvenyesIg >= CAST(GETDATE() AS date))
            """, (azonosito,))
            if k.fetchone()[0]:
                raise ValueError(
                    "Az ügyfélnek még van jelenlegi vagy későbbi eszközkapcsolata. "
                    "Előbb rendezd azok érvényességét."
                )

        k.execute(f"UPDATE {tabla} SET Aktiv = ? WHERE {kulcs} = ?",
                  (int(aktiv), azonosito))
        if k.rowcount != 1:
            raise ValueError("A partner állapotának módosítása nem sikerült.")

    _tranzakcio(mentes)


def kapcsolatok_listazasa():
    """Az összes eszköz–ügyfél kapcsolat, a múltbeli és jövőbeli is."""
    return _lekerdezes("""
        SELECT k.EszkozUgyfelKapcsolatID AS Azonosito,
               k.EszkozID, k.UgyfelID, k.KapcsolatTipusID,
               e.LeltariSzam, u.Nev AS Ugyfel, t.Nev AS KapcsolatTipus,
               k.ErvenyesTol, k.ErvenyesIg, k.Megjegyzes,
               CASE
                   WHEN k.ErvenyesTol > CAST(GETDATE() AS date) THEN N'Jövőbeli'
                   WHEN k.ErvenyesIg < CAST(GETDATE() AS date) THEN N'Lejárt'
                   ELSE N'Érvényes'
               END AS Allapot
        FROM partner.EszkozUgyfelKapcsolat k
        JOIN eszkoz.Eszkoz e ON k.EszkozID = e.EszkozID
        JOIN partner.Ugyfel u ON k.UgyfelID = u.UgyfelID
        JOIN torzs.KapcsolatTipus t ON k.KapcsolatTipusID = t.KapcsolatTipusID
        ORDER BY k.ErvenyesTol DESC, k.EszkozUgyfelKapcsolatID DESC
    """)


def kapcsolat_valasztok(eszkoz_id=None, ugyfel_id=None, tipus_id=None):
    ugyfelek = _lekerdezes("""
        SELECT UgyfelID, Nev FROM partner.Ugyfel
        WHERE Aktiv = 1 OR UgyfelID = ? ORDER BY Nev
    """, (ugyfel_id,))
    eszkozok = _lekerdezes("""
        SELECT EszkozID, LeltariSzam FROM eszkoz.Eszkoz
        WHERE Aktiv = 1 OR EszkozID = ? ORDER BY LeltariSzam
    """, (eszkoz_id,))
    tipusok = _lekerdezes("""
        SELECT KapcsolatTipusID, Nev FROM torzs.KapcsolatTipus
        WHERE Aktiv = 1 OR KapcsolatTipusID = ? ORDER BY Nev
    """, (tipus_id,))
    return eszkozok, ugyfelek, tipusok


# A kapcsolat mentése az érvényességi időszak és a kiválasztott rekordok ellenőrzésével történik.
def kapcsolat_mentese(azonosito, eszkoz_id, ugyfel_id, tipus_id,
                      ervenyes_tol, ervenyes_ig, megjegyzes):
    kezdet = _datum(ervenyes_tol, kotelezo=True)
    veg = _datum(ervenyes_ig)
    if veg is not None and veg < kezdet:
        raise ValueError("A befejezés dátuma nem lehet korábbi a kezdésnél.")
    megjegyzes = _rovidites(megjegyzes, 500, "megjegyzés")

    def mentes(k):
        regi = (None, None, None)
        if azonosito is not None:
            k.execute("""
                SELECT EszkozID, UgyfelID, KapcsolatTipusID
                FROM partner.EszkozUgyfelKapcsolat WITH (UPDLOCK, HOLDLOCK)
                WHERE EszkozUgyfelKapcsolatID = ?
            """, (azonosito,))
            regi = k.fetchone()
            if regi is None:
                raise ValueError("A módosítandó kapcsolat nem található.")

        for index, (tabla, kulcs, ertek, uzenet) in enumerate((
            ("eszkoz.Eszkoz", "EszkozID", eszkoz_id, "Az eszköz nem aktív."),
            ("partner.Ugyfel", "UgyfelID", ugyfel_id, "Az ügyfél nem aktív."),
            ("torzs.KapcsolatTipus", "KapcsolatTipusID", tipus_id,
             "A kapcsolattípus nem aktív."),
        )):
            k.execute(f"""
                SELECT 1 FROM {tabla} WITH (UPDLOCK, HOLDLOCK)
                WHERE {kulcs} = ? AND (Aktiv = 1 OR {kulcs} = ?)
            """, (ertek, regi[index]))
            if k.fetchone() is None:
                raise ValueError(uzenet)

        k.execute("""
            SELECT COUNT(*) FROM partner.EszkozUgyfelKapcsolat WITH (UPDLOCK, HOLDLOCK)
            WHERE EszkozID = ? AND UgyfelID = ? AND KapcsolatTipusID = ?
              AND EszkozUgyfelKapcsolatID <> ?
              AND (ErvenyesIg IS NULL OR ErvenyesIg >= ?)
              AND ErvenyesTol <= ?
        """, (eszkoz_id, ugyfel_id, tipus_id, azonosito or -1,
              kezdet.isoformat(), (veg or date.max).isoformat()))
        if k.fetchone()[0]:
            raise ValueError("Azonos eszköz–ügyfél–kapcsolattípus pároshoz "
                             "már van átfedő érvényességi időszak.")

        adatok = (eszkoz_id, ugyfel_id, tipus_id,
                  kezdet.isoformat(), veg.isoformat() if veg else None, megjegyzes)
        if azonosito is None:
            k.execute("""
                INSERT INTO partner.EszkozUgyfelKapcsolat
                    (EszkozID, UgyfelID, KapcsolatTipusID,
                     ErvenyesTol, ErvenyesIg, Megjegyzes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, adatok)
        else:
            k.execute("""
                UPDATE partner.EszkozUgyfelKapcsolat
                SET EszkozID = ?, UgyfelID = ?, KapcsolatTipusID = ?,
                    ErvenyesTol = ?, ErvenyesIg = ?, Megjegyzes = ?
                WHERE EszkozUgyfelKapcsolatID = ?
            """, (*adatok, azonosito))
            if k.rowcount != 1:
                raise ValueError("A módosítandó kapcsolat nem található.")

    _tranzakcio(mentes)


def kapcsolat_lezarasa(azonosito, datum):
    """Érvényesség végét állítja; a megadott nap még érvényes."""
    veg = _datum(datum, kotelezo=True)

    def mentes(k):
        k.execute("""
            SELECT ErvenyesTol, ErvenyesIg
            FROM partner.EszkozUgyfelKapcsolat WITH (UPDLOCK, HOLDLOCK)
            WHERE EszkozUgyfelKapcsolatID = ?
        """, (azonosito,))
        kapcsolat = k.fetchone()
        if kapcsolat is None:
            raise ValueError("A kapcsolat nem található.")
        if veg < kapcsolat.ErvenyesTol:
            raise ValueError("A lezárás nem lehet korábbi a kezdőnapnál.")
        if kapcsolat.ErvenyesIg is not None and kapcsolat.ErvenyesIg <= veg:
            raise ValueError("A kapcsolat már ezen vagy egy korábbi napon lezárul.")
        k.execute("""
            UPDATE partner.EszkozUgyfelKapcsolat
            SET ErvenyesIg = ?
            WHERE EszkozUgyfelKapcsolatID = ?
        """, (veg.isoformat(), azonosito))
        if k.rowcount != 1:
            raise ValueError("A lezárás nem sikerült.")

    _tranzakcio(mentes)



NEZETEK = ("Ügyfelek", "Beszállítók", "Eszköz–ügyfél kapcsolatok")


# A felület partneradatokat és eszköz–ügyfél kapcsolatokat jelenít meg és szerkeszt.
class PartnerekFelulet(ctk.CTkFrame):
    def __init__(self, szulo):
        super().__init__(szulo, fg_color="transparent")
        self.nezet = "Ügyfelek"
        self.allapot = "Aktív"
        self.keresett = ""
        self.megjelenites()

    def nezet_valtas(self, uj_nezet):
        self.nezet = uj_nezet
        self.allapot = "Összes" if uj_nezet == NEZETEK[2] else "Aktív"
        self.keresett = ""
        self.megjelenites()

    def allapot_valtas(self, uj_allapot):
        self.allapot = uj_allapot
        self.megjelenites()

    def megjelenites(self):
        for elem in self.winfo_children():
            elem.destroy()

        menu = ctk.CTkSegmentedButton(
            self, values=list(NEZETEK), command=self.nezet_valtas
        )
        menu.pack(anchor="w", padx=10, pady=(0, 12))
        menu.set(self.nezet)

        vezerlo = ctk.CTkFrame(self, fg_color="transparent")
        vezerlo.pack(fill="x", padx=10, pady=(0, 10))

        kapcsolat_nezet = self.nezet == NEZETEK[2]
        allapotok = (["Összes", "Érvényes", "Jövőbeli", "Lejárt"]
                     if kapcsolat_nezet else ["Aktív", "Inaktív"])
        valto = ctk.CTkSegmentedButton(
            vezerlo, values=allapotok, command=self.allapot_valtas
        )
        valto.pack(side="left", padx=(0, 12))
        valto.set(self.allapot)

        if kapcsolat_nezet or self.allapot == "Aktív":
            muveleti_gomb(
                vezerlo, text="+ Új kapcsolat" if kapcsolat_nezet else "+ Új partner",
                width=125,
                command=self.kapcsolat_urlap if kapcsolat_nezet else self.partner_urlap
            ).pack(side="left", padx=5)

        kereso = ctk.CTkEntry(
            vezerlo, width=190, placeholder_text="Keresés..."
        )
        kereso.pack(side="left", padx=5)
        kereso.insert(0, self.keresett)

        def kereses():
            self.keresett = kereso.get().strip()
            self.megjelenites()

        ctk.CTkButton(
            vezerlo, text="Keresés", width=80, command=kereses
        ).pack(side="left", padx=4)
        kereso.bind("<Return>", lambda _esemeny: kereses())
        ctk.CTkButton(
            vezerlo, text="Törlés", width=70,
            command=lambda: self.kereses_torlese()
        ).pack(side="left", padx=4)

        try:
            if kapcsolat_nezet:
                sorok = kapcsolatok_listazasa()
                if self.allapot != "Összes":
                    sorok = [s for s in sorok if s.Allapot == self.allapot]
            else:
                sorok = partnerek_listazasa(self.nezet, self.allapot == "Aktív")
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba), parent=self)
            return

        if self.keresett:
            keresett = self.keresett.casefold()
            if kapcsolat_nezet:
                sorok = [s for s in sorok if any(keresett in str(ertek).casefold()
                         for ertek in (s.LeltariSzam, s.Ugyfel, s.KapcsolatTipus, s.Allapot))]
            else:
                sorok = [s for s in sorok if any(keresett in str(ertek or "").casefold()
                         for ertek in (s.Nev, s.Adoszam, s.KapcsolattartoNev,
                                       s.KapcsolattartoEmail, s.KapcsolattartoTelefon))]

        ctk.CTkLabel(
            self, text=f"{self.nezet} – találatok: {len(sorok)}", anchor="w"
        ).pack(fill="x", padx=10, pady=5)

        tabla = ctk.CTkScrollableFrame(self)
        tabla.pack(fill="both", expand=True, padx=10, pady=5)

        if kapcsolat_nezet:
            fejlecek = ("Eszköz", "Ügyfél", "Kapcsolat típusa",
                        "Kezdet", "Vég", "Állapot")
            oszlopszelesseg = (120, 170, 125, 95, 95, 85)
        else:
            fejlecek = ("Név", "Adószám", "Kapcsolattartó", "E-mail",
                        "Aktív kapcsolatok" if self.nezet == "Ügyfelek" else "Beszerzések")
            oszlopszelesseg = (175, 125, 145, 180, 115)

        for i, fejlec in enumerate((*fejlecek, "Műveletek")):
            ctk.CTkLabel(
                tabla, text=fejlec, font=ctk.CTkFont(weight="bold"),
                width=oszlopszelesseg[i] if i < len(oszlopszelesseg) else 210,
                anchor="w"
            ).grid(row=0, column=i, padx=5, pady=8, sticky="w")

        if not sorok:
            ctk.CTkLabel(tabla, text="Nincs a feltételeknek megfelelő adat.").grid(
                row=1, column=0, columnspan=len(fejlecek) + 1, pady=30
            )
            return

        for sorindex, sor in enumerate(sorok, 1):
            if kapcsolat_nezet:
                adatok = (sor.LeltariSzam, sor.Ugyfel, sor.KapcsolatTipus,
                          str(sor.ErvenyesTol), str(sor.ErvenyesIg or "–"), sor.Allapot)
            else:
                adatok = (sor.Nev, sor.Adoszam, sor.KapcsolattartoNev,
                          sor.KapcsolattartoEmail, sor.Hivatkozasok)

            for oszlop, adat in enumerate(adatok):
                szelesseg = oszlopszelesseg[oszlop]
                ctk.CTkLabel(
                    tabla, text=str(adat) if adat is not None else "–",
                    width=szelesseg, anchor="w", wraplength=szelesseg
                ).grid(row=sorindex, column=oszlop, padx=5, pady=6, sticky="w")

            gombok = ctk.CTkFrame(tabla, fg_color="transparent")
            gombok.grid(row=sorindex, column=len(fejlecek), padx=4, pady=5)

            if kapcsolat_nezet:
                muveleti_gomb(
                    gombok, text="Szerkesztés", width=90,
                    command=lambda s=sor: self.kapcsolat_urlap(s)
                ).pack(side="left", padx=3)
                if sor.Allapot != "Lejárt":
                    muveleti_gomb(
                        gombok, text="Lezárás", width=80,
                        command=lambda s=sor: self.kapcsolat_lezaras_urlap(s)
                    ).pack(side="left", padx=3)
            elif self.allapot == "Aktív":
                muveleti_gomb(
                    gombok, text="Szerkesztés", width=90,
                    command=lambda s=sor: self.partner_urlap(s)
                ).pack(side="left", padx=3)
                muveleti_gomb(
                    gombok, text="Inaktiválás", width=95,
                    fg_color="#B33A3A", hover_color="#902E2E",
                    command=lambda s=sor: self.partner_allapot(s, False)
                ).pack(side="left", padx=3)
            else:
                muveleti_gomb(
                    gombok, text="Visszaállítás", width=115,
                    command=lambda s=sor: self.partner_allapot(s, True)
                ).pack(side="left", padx=3)

    def kereses_torlese(self):
        self.keresett = ""
        self.megjelenites()

    def partner_allapot(self, sor, uj_allapot):
        ige = "visszaállítod" if uj_allapot else "inaktiválod"
        if not messagebox.askyesno(
            "Megerősítés", f"Biztosan {ige} ezt a partnert?\n\n{sor.Nev}",
            parent=self
        ):
            return
        try:
            partner_aktivitas(self.nezet, sor.Azonosito, uj_allapot)
        except Exception as hiba:
            messagebox.showerror("Nem sikerült", str(hiba), parent=self)
            return
        self.megjelenites()

    def _ablak(self, cim, magassag=700):
        ablak = FelugroAblak(self)
        ablak.title(cim)
        ablak.geometry(f"780x{magassag}")
        ablak.minsize(700, 570)
        ablak.transient(self.winfo_toplevel())
        keret = ctk.CTkScrollableFrame(ablak)
        keret.pack(fill="both", expand=True, padx=20, pady=20)
        ablak.grab_set()
        return ablak, keret

    @staticmethod
    def _mezo(keret, nev, ertek=""):
        ctk.CTkLabel(keret, text=nev, anchor="w").pack(
            fill="x", pady=(12, 4)
        )
        mezo = ctk.CTkEntry(keret)
        mezo.pack(fill="x")
        mezo.insert(0, "" if ertek is None else str(ertek))
        return mezo

    @staticmethod
    def _megjegyzes(keret, ertek=""):
        ctk.CTkLabel(keret, text="Megjegyzés", anchor="w").pack(
            fill="x", pady=(12, 4)
        )
        mezo = ctk.CTkTextbox(keret, height=95)
        mezo.pack(fill="x")
        mezo.insert("1.0", ertek or "")
        return mezo

    def partner_urlap(self, rekord=None):
        tipus = self.nezet
        ablak, keret = self._ablak(
            f"{tipus} – {'Szerkesztés' if rekord else 'Új felvitel'}"
        )
        nev = self._mezo(keret, "Név *", rekord.Nev if rekord else "")
        adoszam = self._mezo(keret, "Adószám", rekord.Adoszam if rekord else "")
        kapcsolattarto = self._mezo(
            keret, "Kapcsolattartó neve", rekord.KapcsolattartoNev if rekord else ""
        )
        email = self._mezo(
            keret, "Kapcsolattartó e-mail-címe",
            rekord.KapcsolattartoEmail if rekord else ""
        )
        telefon = self._mezo(
            keret, "Kapcsolattartó telefonszáma",
            rekord.KapcsolattartoTelefon if rekord else ""
        )
        megjegyzes = self._megjegyzes(keret, rekord.Megjegyzes if rekord else "")

        def mentes():
            try:
                partner_mentese(
                    tipus, rekord.Azonosito if rekord else None,
                    nev.get(), adoszam.get(), kapcsolattarto.get(),
                    email.get(), telefon.get(),
                    megjegyzes.get("1.0", "end").strip()
                )
            except Exception as hiba:
                messagebox.showerror("Mentési hiba", str(hiba), parent=ablak)
                return
            ablak.destroy()
            self.megjelenites()
            messagebox.showinfo("Siker", "A partner adatai mentve.", parent=self)

        muveleti_gomb(
            keret, text="Mentés", height=40, command=mentes
        ).pack(fill="x", pady=25)

    @staticmethod
    def _valaszto(keret, cim, elemek, azonosito=None):
        ctk.CTkLabel(keret, text=cim, anchor="w").pack(
            fill="x", pady=(12, 4)
        )
        opciok = {f"{nev} (ID: {kulcs})": kulcs for kulcs, nev in elemek}
        menu = ctk.CTkOptionMenu(keret, values=list(opciok))
        menu.pack(fill="x")
        menu.set(next(
            (nev for nev, kulcs in opciok.items() if kulcs == azonosito),
            next(iter(opciok))
        ))
        return menu, opciok

    def kapcsolat_urlap(self, rekord=None):
        try:
            eszkozok, ugyfelek, tipusok = kapcsolat_valasztok(
                rekord.EszkozID if rekord else None,
                rekord.UgyfelID if rekord else None,
                rekord.KapcsolatTipusID if rekord else None,
            )
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba), parent=self)
            return
        if not eszkozok or not ugyfelek or not tipusok:
            messagebox.showwarning(
                "Hiányzó adat",
                "Kapcsolat rögzítéséhez aktív eszköz, ügyfél és kapcsolattípus kell.",
                parent=self
            )
            return
        if rekord and (
            rekord.EszkozID not in {s.EszkozID for s in eszkozok}
            or rekord.UgyfelID not in {s.UgyfelID for s in ugyfelek}
            or rekord.KapcsolatTipusID not in {s.KapcsolatTipusID for s in tipusok}
        ):
            messagebox.showwarning(
                "Inaktív hivatkozás",
                "A kapcsolat egyik hivatkozott adata már inaktív. "
                "A történeti adatok megtekinthetők, de ezen az űrlapon nem módosíthatók.",
                parent=self
            )
            return

        ablak, keret = self._ablak(
            "Eszköz–ügyfél kapcsolat – " + ("Szerkesztés" if rekord else "Új felvitel")
        )
        eszkoz_menu, eszkoz_opciok = self._valaszto(
            keret, "Eszköz *", [(s.EszkozID, s.LeltariSzam) for s in eszkozok],
            rekord.EszkozID if rekord else None
        )
        ugyfel_menu, ugyfel_opciok = self._valaszto(
            keret, "Ügyfél *", [(s.UgyfelID, s.Nev) for s in ugyfelek],
            rekord.UgyfelID if rekord else None
        )
        tipus_menu, tipus_opciok = self._valaszto(
            keret, "Kapcsolattípus *", [(s.KapcsolatTipusID, s.Nev) for s in tipusok],
            rekord.KapcsolatTipusID if rekord else None
        )
        kezdet = self._mezo(
            keret, "Érvényesség kezdete (ÉÉÉÉ-HH-NN) *",
            rekord.ErvenyesTol if rekord else date.today().isoformat()
        )
        veg = self._mezo(
            keret, "Érvényesség vége (ÉÉÉÉ-HH-NN, nem kötelező)",
            rekord.ErvenyesIg if rekord else ""
        )
        ctk.CTkLabel(
            keret, text="A megadott végdátumon a kapcsolat még érvényes.",
            anchor="w"
        ).pack(fill="x", pady=(8, 0))
        megjegyzes = self._megjegyzes(keret, rekord.Megjegyzes if rekord else "")

        def mentes():
            try:
                kapcsolat_mentese(
                    rekord.Azonosito if rekord else None,
                    eszkoz_opciok[eszkoz_menu.get()],
                    ugyfel_opciok[ugyfel_menu.get()],
                    tipus_opciok[tipus_menu.get()],
                    kezdet.get(), veg.get(),
                    megjegyzes.get("1.0", "end").strip()
                )
            except Exception as hiba:
                messagebox.showerror("Mentési hiba", str(hiba), parent=ablak)
                return
            ablak.destroy()
            self.allapot = "Összes"
            self.megjelenites()
            messagebox.showinfo("Siker", "A kapcsolat adatai mentve.", parent=self)

        muveleti_gomb(
            keret, text="Kapcsolat mentése", height=40, command=mentes
        ).pack(fill="x", pady=25)

    def kapcsolat_lezaras_urlap(self, rekord):
        ablak, keret = self._ablak("Kapcsolat lezárása", magassag=570)
        ctk.CTkLabel(
            keret,
            text=f"{rekord.LeltariSzam} – {rekord.Ugyfel} ({rekord.KapcsolatTipus})",
            wraplength=650
        ).pack(fill="x", pady=12)
        datum = self._mezo(
            keret, "Érvényesség utolsó napja (ÉÉÉÉ-HH-NN)", date.today().isoformat()
        )
        ctk.CTkLabel(
            keret,
            text="A lezárás napja még érvényes nap. Ha ma zárod le, "
                 "a kapcsolat holnaptól lesz lejárt.",
            wraplength=650
        ).pack(fill="x", pady=15)

        def mentes():
            try:
                kapcsolat_lezarasa(rekord.Azonosito, datum.get())
            except Exception as hiba:
                messagebox.showerror("Lezárási hiba", str(hiba), parent=ablak)
                return
            ablak.destroy()
            self.allapot = "Összes"
            self.megjelenites()
            messagebox.showinfo("Siker", "A kapcsolat végdátuma mentve.", parent=self)

        muveleti_gomb(
            keret, text="Lezárás mentése", height=40, command=mentes
        ).pack(fill="x", pady=20)


from api import bekotes
bekotes(globals(), "partnerek")
