"""Telephelyek, termek és rackek kezelése."""


from adatbazis import kapcsolat_letrehozasa, lekerdezes as _lekerdezes, tranzakcio as _tranzakcio
from felulet_seged import FelugroAblak, muveleti_gomb
from tkinter import messagebox
import customtkinter as ctk


TABLAK = {
    "Telephelyek": ("infrastruktura.Telephely", "TelephelyID"),
    "Termek": ("infrastruktura.Terem", "TeremID"),
    "Helyek és rackek": ("infrastruktura.Hely", "HelyID"),
}


# A közös mentőfüggvény rögzített táblanevekkel végzi az infrastruktúra rekordjainak beszúrását és módosítását.
def _sor_mentese(kurzor, tabla, kulcs, azonosito, mezok, ertekek):
    """Beszúrás/módosítás, csak belső, rögzített táblanevekkel."""
    if azonosito is None:
        oszlopok = ", ".join(mezok)
        helyek = ", ".join("?" for _ in mezok)
        kurzor.execute(
            f"INSERT INTO {tabla} ({oszlopok}) OUTPUT INSERTED.{kulcs} "
            f"VALUES ({helyek})", tuple(ertekek)
        )
        return kurzor.fetchone()[0]

    beallitasok = ", ".join(f"{mezo} = ?" for mezo in mezok)
    kurzor.execute(
        f"UPDATE {tabla} SET {beallitasok} "
        f"WHERE {kulcs} = ? AND Aktiv = 1", (*ertekek, azonosito)
    )
    if kurzor.rowcount != 1:
        raise ValueError("A módosítandó aktív rekord nem található.")
    return azonosito


def _letezik(kurzor, sql, parameterek):
    kurzor.execute(sql, parameterek)
    return kurzor.fetchone()[0] > 0


def listazas(tipus, aktiv=True):
    if tipus == "Telephelyek":
        sql = """
            SELECT t.TelephelyID, t.Nev, t.Varos, t.Cim, t.Aktiv,
                   (SELECT COUNT(*) FROM infrastruktura.Terem r
                    WHERE r.TelephelyID = t.TelephelyID AND r.Aktiv = 1)
                   AS TermekSzama,
                   (SELECT COUNT(*) FROM infrastruktura.Hely h
                    WHERE h.TelephelyID = t.TelephelyID AND h.Aktiv = 1)
                   AS HelyekSzama
            FROM infrastruktura.Telephely t
            WHERE t.Aktiv = ?
            ORDER BY t.Nev
        """
    elif tipus == "Termek":
        sql = """
            SELECT r.TeremID, r.TelephelyID, r.Nev, r.Leiras, r.Aktiv,
                   t.Nev AS Telephely,
                   (SELECT COUNT(*) FROM infrastruktura.Hely h
                    WHERE h.TeremID = r.TeremID AND h.Aktiv = 1)
                   AS HelyekSzama
            FROM infrastruktura.Terem r
            JOIN infrastruktura.Telephely t ON r.TelephelyID = t.TelephelyID
            WHERE r.Aktiv = ?
            ORDER BY t.Nev, r.Nev
        """
    elif tipus == "Helyek és rackek":
        sql = """
            SELECT h.HelyID, h.TelephelyID, h.TeremID, h.HelyTipusID,
                   h.Nev, h.Leiras, h.Aktiv,
                   t.Nev AS Telephely, tr.Nev AS Terem,
                   ht.Nev AS Tipus, ht.Kod AS TipusKod,
                   rk.MagassagU AS RackMagassag,
                   (SELECT COUNT(*) FROM eszkoz.Eszkoz e
                    WHERE e.HelyID = h.HelyID AND e.Aktiv = 1)
                   AS EszkozokSzama,
                   (SELECT COALESCE(SUM(COALESCE(m.MagassagU, 0)), 0)
                    FROM eszkoz.Eszkoz e
                    JOIN torzs.Modell m ON e.ModellID = m.ModellID
                    WHERE e.HelyID = h.HelyID AND e.Aktiv = 1
                      AND e.RackPozicioKezdet IS NOT NULL)
                   AS FoglaltU
            FROM infrastruktura.Hely h
            JOIN infrastruktura.Telephely t ON h.TelephelyID = t.TelephelyID
            LEFT JOIN infrastruktura.Terem tr ON h.TeremID = tr.TeremID
            JOIN torzs.HelyTipus ht ON h.HelyTipusID = ht.HelyTipusID
            LEFT JOIN infrastruktura.Rack rk ON rk.HelyID = h.HelyID
            WHERE h.Aktiv = ?
            ORDER BY t.Nev, tr.Nev, h.Nev
        """
    else:
        raise ValueError("Ismeretlen infrastruktúra-nézet.")
    return _lekerdezes(sql, (int(aktiv),))


def valasztasi_adatok():
    """Aktív telephelyek, termek és helytípusok az űrlapokhoz."""
    telephelyek = _lekerdezes("""
        SELECT TelephelyID, Nev FROM infrastruktura.Telephely
        WHERE Aktiv = 1 ORDER BY Nev
    """)
    termek = _lekerdezes("""
        SELECT r.TeremID, r.TelephelyID, r.Nev
        FROM infrastruktura.Terem r
        JOIN infrastruktura.Telephely t ON r.TelephelyID = t.TelephelyID
        WHERE r.Aktiv = 1 AND t.Aktiv = 1
        ORDER BY r.Nev
    """)
    tipusok = _lekerdezes("""
        SELECT HelyTipusID, Kod, Nev FROM torzs.HelyTipus
        WHERE Aktiv = 1 ORDER BY Nev
    """)
    return telephelyek, termek, tipusok


def telephely_mentese(azonosito, nev, varos, cim):
    if not nev.strip():
        raise ValueError("A telephely neve kötelező.")

    def mentes(k):
        _sor_mentese(k, *TABLAK["Telephelyek"], azonosito,
                        ("Nev", "Varos", "Cim"),
                        (nev.strip(), varos.strip() or None, cim.strip() or None))
    _tranzakcio(mentes)


def terem_mentese(azonosito, telephely_id, nev, leiras):
    if not nev.strip():
        raise ValueError("A terem neve kötelező.")

    def mentes(k):
        if not _letezik(k, """
            SELECT COUNT(*) FROM infrastruktura.Telephely WITH (UPDLOCK, HOLDLOCK)
            WHERE TelephelyID = ? AND Aktiv = 1
        """, (telephely_id,)):
            raise ValueError("A telephely nem aktív vagy nem található.")

        if azonosito is not None and _letezik(k, """
            SELECT COUNT(*) FROM infrastruktura.Terem
            WHERE TeremID = ? AND TelephelyID <> ?
        """, (azonosito, telephely_id)) and _letezik(k, """
            SELECT COUNT(*) FROM infrastruktura.Hely WHERE TeremID = ?
        """, (azonosito,)):
            raise ValueError("Helyeket tartalmazó terem nem helyezhető át másik telephelyre.")

        _sor_mentese(k, *TABLAK["Termek"], azonosito,
                        ("TelephelyID", "Nev", "Leiras"),
                        (telephely_id, nev.strip(), leiras.strip() or None))
    _tranzakcio(mentes)


def hely_mentese(azonosito, telephely_id, terem_id, tipus_id,
                  nev, leiras, rack_magassag):
    if not nev.strip():
        raise ValueError("A hely neve kötelező.")

    def mentes(k):
        if not _letezik(k, """
            SELECT COUNT(*) FROM infrastruktura.Telephely WITH (UPDLOCK, HOLDLOCK)
            WHERE TelephelyID = ? AND Aktiv = 1
        """, (telephely_id,)):
            raise ValueError("A telephely nem aktív.")
        if terem_id is not None and not _letezik(k, """
            SELECT COUNT(*) FROM infrastruktura.Terem WITH (UPDLOCK, HOLDLOCK)
            WHERE TeremID = ? AND TelephelyID = ? AND Aktiv = 1
        """, (terem_id, telephely_id)):
            raise ValueError("A terem nem aktív, vagy nem ehhez a telephelyhez tartozik.")

        k.execute("""
            SELECT Kod FROM torzs.HelyTipus WHERE HelyTipusID = ? AND Aktiv = 1
        """, (tipus_id,))
        tipus = k.fetchone()
        if tipus is None:
            raise ValueError("A helytípus nem választható.")
        rack = tipus.Kod == "RACK"
        if rack:
            if rack_magassag is None or not 1 <= rack_magassag <= 255:
                raise ValueError("A rack magassága 1–255 U lehet.")
        elif rack_magassag is not None:
            raise ValueError("U-magasság csak rackhez adható meg.")

        if azonosito is not None:
            k.execute("""
                SELECT TelephelyID, TeremID, HelyTipusID
                FROM infrastruktura.Hely WITH (UPDLOCK, HOLDLOCK)
                WHERE HelyID = ? AND Aktiv = 1
            """, (azonosito,))
            regi = k.fetchone()
            if regi is None:
                raise ValueError("A módosítandó hely nem található.")

            strukturavaltozas = (
                regi.TelephelyID != telephely_id or regi.TeremID != terem_id
                or regi.HelyTipusID != tipus_id
            )
            if strukturavaltozas and _letezik(k, """
                SELECT COUNT(*) FROM eszkoz.Eszkoz WHERE HelyID = ?
            """, (azonosito,)):
                raise ValueError(
                    "Eszközhöz rendelt hely telephelye, terme vagy típusa nem változtatható. "
                    "Előbb mozgasd át az eszközöket."
                )

            if rack and _letezik(k, """
                SELECT COUNT(*)
                FROM eszkoz.Eszkoz e
                JOIN torzs.Modell m ON e.ModellID = m.ModellID
                WHERE e.HelyID = ? AND e.Aktiv = 1
                  AND e.RackPozicioKezdet IS NOT NULL
                  AND (m.MagassagU IS NULL OR
                       e.RackPozicioKezdet + m.MagassagU - 1 > ?)
            """, (azonosito, rack_magassag)):
                raise ValueError("A kisebb rackből kilógna legalább egy eszköz.")

        uj_id = _sor_mentese(k, *TABLAK["Helyek és rackek"], azonosito,
                             ("TelephelyID", "TeremID", "HelyTipusID", "Nev", "Leiras"),
                             (telephely_id, terem_id, tipus_id,
                              nev.strip(), leiras.strip() or None))
        if rack:
            k.execute("""
                UPDATE infrastruktura.Rack SET MagassagU = ? WHERE HelyID = ?
            """, (rack_magassag, uj_id))
            if k.rowcount == 0:
                k.execute("""
                    INSERT INTO infrastruktura.Rack (HelyID, MagassagU)
                    VALUES (?, ?)
                """, (uj_id, rack_magassag))
        else:
            k.execute("DELETE FROM infrastruktura.Rack WHERE HelyID = ?", (uj_id,))
    _tranzakcio(mentes)


def aktivitas_valtasa(tipus, azonosito, aktiv):
    """Inaktiválás/visszaállítás; aktív alárendelt rekordokat védi."""
    if tipus not in TABLAK:
        raise ValueError("Ismeretlen infrastruktúra-nézet.")
    tabla, kulcs = TABLAK[tipus]

    def modositas(k):
        k.execute(f"SELECT Aktiv FROM {tabla} WITH (UPDLOCK, HOLDLOCK) WHERE {kulcs} = ?",
                  (azonosito,))
        sor = k.fetchone()
        if sor is None or bool(sor.Aktiv) == bool(aktiv):
            raise ValueError("A rekord nem található, vagy már ebben az állapotban van.")

        if not aktiv:
            if tipus == "Telephelyek":
                if _letezik(k, """
                    SELECT COUNT(*) FROM infrastruktura.Terem
                    WHERE TelephelyID = ? AND Aktiv = 1
                """, (azonosito,)) or _letezik(k, """
                    SELECT COUNT(*) FROM infrastruktura.Hely
                    WHERE TelephelyID = ? AND Aktiv = 1
                """, (azonosito,)):
                    raise ValueError("Először a telephely aktív termeit és helyeit inaktiváld.")
            elif tipus == "Termek":
                if _letezik(k, """
                    SELECT COUNT(*) FROM infrastruktura.Hely
                    WHERE TeremID = ? AND Aktiv = 1
                """, (azonosito,)):
                    raise ValueError("Először a terem aktív helyeit inaktiváld.")
            else:
                if _letezik(k, """
                    SELECT COUNT(*) FROM eszkoz.Eszkoz
                    WHERE HelyID = ? AND Aktiv = 1
                """, (azonosito,)):
                    raise ValueError("Először helyezd át vagy inaktiváld az itt lévő aktív eszközöket.")
        else:
            if tipus == "Termek" and not _letezik(k, """
                SELECT COUNT(*) FROM infrastruktura.Terem r
                JOIN infrastruktura.Telephely t ON r.TelephelyID = t.TelephelyID
                WHERE r.TeremID = ? AND t.Aktiv = 1
            """, (azonosito,)):
                raise ValueError("Előbb a telephelyet állítsd vissza.")
            if tipus == "Helyek és rackek" and not _letezik(k, """
                SELECT COUNT(*) FROM infrastruktura.Hely h
                JOIN infrastruktura.Telephely t ON h.TelephelyID = t.TelephelyID
                LEFT JOIN infrastruktura.Terem r ON h.TeremID = r.TeremID
                WHERE h.HelyID = ? AND t.Aktiv = 1
                  AND (h.TeremID IS NULL OR r.Aktiv = 1)
            """, (azonosito,)):
                raise ValueError("Előbb a telephelyet és a termet állítsd vissza.")

        k.execute(f"UPDATE {tabla} SET Aktiv = ? WHERE {kulcs} = ?", (int(aktiv), azonosito))
        if k.rowcount != 1:
            raise ValueError("A státuszmódosítás nem sikerült.")

    _tranzakcio(modositas)



NEZETEK = ("Telephelyek", "Termek", "Helyek és rackek")


# A felület telephelyek, termek, helyek és rackek között vált, majd az adott űrlapot jeleníti meg.
class InfrastrukturaFelulet(ctk.CTkFrame):
    def __init__(self, szulo):
        super().__init__(szulo, fg_color="transparent")
        self.nezet = NEZETEK[0]
        self.allapot = "Aktív"
        self.megjelenites()

    def megjelenites(self):
        for elem in self.winfo_children():
            elem.destroy()

        nezet_valto = ctk.CTkSegmentedButton(
            self, values=list(NEZETEK), command=self.nezet_valtas
        )
        nezet_valto.pack(anchor="w", padx=10, pady=(0, 12))
        nezet_valto.set(self.nezet)

        vezerlok = ctk.CTkFrame(self, fg_color="transparent")
        vezerlok.pack(fill="x", padx=10, pady=(0, 10))
        allapot_valto = ctk.CTkSegmentedButton(
            vezerlok, values=["Aktív", "Inaktív"], command=self.allapot_valtas
        )
        allapot_valto.pack(side="left", padx=(0, 15))
        allapot_valto.set(self.allapot)

        if self.allapot == "Aktív":
            muveleti_gomb(
                vezerlok, text="+ Új felvitele", width=140,
                command=lambda: self.urlap()
            ).pack(side="left")

        try:
            sorok = listazas(self.nezet, self.allapot == "Aktív")
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba), parent=self)
            return

        ctk.CTkLabel(
            self, text=f"{self.nezet} – {self.allapot.lower()} rekordok: {len(sorok)}",
            anchor="w"
        ).pack(fill="x", padx=10, pady=5)

        tabla = ctk.CTkScrollableFrame(self)
        tabla.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        if self.nezet == "Telephelyek":
            fejlecek = ("Név", "Város", "Cím", "Termek", "Helyek")
            adat = lambda s: (s.Nev, s.Varos, s.Cim, s.TermekSzama, s.HelyekSzama)
            azonosito = "TelephelyID"
        elif self.nezet == "Termek":
            fejlecek = ("Telephely", "Terem", "Leírás", "Helyek")
            adat = lambda s: (s.Telephely, s.Nev, s.Leiras, s.HelyekSzama)
            azonosito = "TeremID"
        else:
            fejlecek = ("Telephely", "Terem", "Hely", "Típus", "Eszközök", "Rack foglaltság")
            adat = lambda s: (
                s.Telephely, s.Terem, s.Nev, s.Tipus,
                s.EszkozokSzama,
                f"{s.FoglaltU}/{s.RackMagassag} U" if s.RackMagassag else "–"
            )
            azonosito = "HelyID"

        szelesseg = 115 if self.nezet != "Helyek és rackek" else 105
        for oszlop, cim in enumerate((*fejlecek, "Műveletek")):
            ctk.CTkLabel(
                tabla, text=cim, font=ctk.CTkFont(weight="bold"),
                width=szelesseg, anchor="w"
            ).grid(row=0, column=oszlop, padx=5, pady=8, sticky="w")

        if not sorok:
            ctk.CTkLabel(tabla, text="Ebben a nézetben még nincs adat.").grid(
                row=1, column=0, columnspan=len(fejlecek) + 1, pady=20
            )
            return

        for sorindex, sor in enumerate(sorok, 1):
            for oszlop, ertek in enumerate(adat(sor)):
                ctk.CTkLabel(
                    tabla, text=str(ertek) if ertek is not None else "–",
                    width=szelesseg, anchor="w", wraplength=szelesseg + 15
                ).grid(row=sorindex, column=oszlop, padx=5, pady=6, sticky="w")

            gombok = ctk.CTkFrame(tabla, fg_color="transparent")
            gombok.grid(row=sorindex, column=len(fejlecek), padx=4, pady=5)
            if self.allapot == "Aktív":
                muveleti_gomb(
                    gombok, text="Szerkesztés", width=90,
                    command=lambda s=sor: self.urlap(s)
                ).pack(side="left", padx=2)
                muveleti_gomb(
                    gombok, text="Inaktiválás", width=90,
                    fg_color="#B33A3A", hover_color="#902E2E",
                    command=lambda a=getattr(sor, azonosito), n=sor.Nev:
                        self.aktivitas(a, n, False)
                ).pack(side="left", padx=2)
            else:
                muveleti_gomb(
                    gombok, text="Visszaállítás", width=110,
                    command=lambda a=getattr(sor, azonosito), n=sor.Nev:
                        self.aktivitas(a, n, True)
                ).pack(side="left", padx=2)

    def nezet_valtas(self, ertek):
        self.nezet = ertek
        self.megjelenites()

    def allapot_valtas(self, ertek):
        self.allapot = ertek
        self.megjelenites()

    def aktivitas(self, azonosito, nev, aktiv):
        muvelet = "visszaállítod" if aktiv else "inaktiválod"
        if not messagebox.askyesno(
            "Megerősítés", f"Biztosan {muvelet}?\n\n{nev}", parent=self
        ):
            return
        try:
            aktivitas_valtasa(self.nezet, azonosito, aktiv)
        except Exception as hiba:
            messagebox.showerror("Nem sikerült", str(hiba), parent=self)
            return
        self.megjelenites()

    def urlap(self, rekord=None):
        try:
            telephelyek, termek, tipusok = valasztasi_adatok()
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba), parent=self)
            return

        if self.nezet != "Telephelyek" and not telephelyek:
            messagebox.showwarning(
                "Hiányzó adat", "Először vegyél fel egy aktív telephelyet.", parent=self
            )
            return
        if self.nezet == "Helyek és rackek" and not tipusok:
            messagebox.showwarning(
                "Hiányzó helytípus", "Nincs aktív helytípus a törzsadatokban.", parent=self
            )
            return

        # A korábbi inaktív kapcsolatot is megmutatom a választóban.
        if rekord and self.nezet != "Telephelyek":
            if rekord.TelephelyID not in [t.TelephelyID for t in telephelyek]:
                messagebox.showwarning(
                    "Inaktív telephely", "Először állítsd vissza a telephelyet.", parent=self
                )
                return
            if self.nezet == "Helyek és rackek":
                if rekord.HelyTipusID not in [t.HelyTipusID for t in tipusok]:
                    messagebox.showwarning(
                        "Inaktív helytípus", "A jelenlegi helytípus nem választható.", parent=self
                    )
                    return
                if rekord.TeremID is not None and rekord.TeremID not in [t.TeremID for t in termek]:
                    messagebox.showwarning(
                        "Inaktív terem", "Először állítsd vissza a termet.", parent=self
                    )
                    return

        ablak = FelugroAblak(self)
        ablak.title(f"{self.nezet} – {'Szerkesztés' if rekord else 'Új felvitel'}")
        ablak.geometry("760x700")
        ablak.minsize(650, 600)
        ablak.transient(self.winfo_toplevel())
        ablak.grab_set()

        keret = ctk.CTkScrollableFrame(ablak)
        keret.pack(fill="both", expand=True, padx=20, pady=20)

        def felirat(szoveg):
            ctk.CTkLabel(keret, text=szoveg, anchor="w").pack(
                fill="x", pady=(12, 4)
            )

        def mezo(cimke, ertek=""):
            felirat(cimke)
            widget = ctk.CTkEntry(keret)
            widget.pack(fill="x")
            widget.insert(0, str(ertek) if ertek is not None else "")
            return widget

        def valaszto(cimke, ertekek, kiv_id=None, parancs=None):
            felirat(cimke)
            opciok = {f"{szoveg} (ID: {az})": az for az, szoveg in ertekek}
            menu = ctk.CTkOptionMenu(
                keret, values=list(opciok), command=parancs
            )
            menu.pack(fill="x")
            kijelolt = next(
                (nev for nev, az in opciok.items() if az == kiv_id),
                next(iter(opciok))
            )
            menu.set(kijelolt)
            return menu, opciok

        nev = mezo("Név *", rekord.Nev if rekord else "")
        if self.nezet == "Telephelyek":
            varos = mezo("Város", rekord.Varos if rekord else "")
            cim = mezo("Cím", rekord.Cim if rekord else "")
        else:
            telephely_menu, telephely_opciok = valaszto(
                "Telephely *", [(s.TelephelyID, s.Nev) for s in telephelyek],
                rekord.TelephelyID if rekord else None
            )

            if self.nezet == "Termek":
                leiras = mezo("Leírás", rekord.Leiras if rekord else "")
            else:
                felirat("Terem (nem kötelező)")
                terem_menu = ctk.CTkOptionMenu(keret, values=["Nincs megadva"])
                terem_menu.pack(fill="x")
                terem_opciok = {"Nincs megadva": None}

                def termek_frissitese(_=None, elso=False):
                    nonlocal terem_opciok
                    telephely_id = telephely_opciok[telephely_menu.get()]
                    terem_opciok = {"Nincs megadva": None}
                    for t in termek:
                        if t.TelephelyID == telephely_id:
                            terem_opciok[f"{t.Nev} (ID: {t.TeremID})"] = t.TeremID
                    terem_menu.configure(values=list(terem_opciok))
                    kijelolt_id = rekord.TeremID if rekord and elso else None
                    terem_menu.set(next(
                        (n for n, az in terem_opciok.items() if az == kijelolt_id),
                        "Nincs megadva"
                    ))

                telephely_menu.configure(command=termek_frissitese)
                termek_frissitese(elso=True)
                tipus_menu, tipus_opciok = valaszto(
                    "Helytípus *",
                    [(t.HelyTipusID, f"{t.Nev} [{t.Kod}]") for t in tipusok],
                    rekord.HelyTipusID if rekord else None
                )
                leiras = mezo("Leírás", rekord.Leiras if rekord else "")
                magassag = mezo(
                    "Rack magassága U-ban (csak rack típus esetén)",
                    rekord.RackMagassag if rekord else ""
                )
                ctk.CTkLabel(
                    keret,
                    text="Rack típus esetén a magasság kötelező (1–255 U). "
                         "Más helytípusnál hagyd üresen.",
                    wraplength=620
                ).pack(pady=12)

        def mentes():
            szoveg = nev.get().strip()
            if not szoveg:
                messagebox.showwarning(
                    "Hiányzó adat", "A név megadása kötelező.", parent=ablak
                )
                return
            try:
                if self.nezet == "Telephelyek":
                    telephely_mentese(
                        rekord.TelephelyID if rekord else None,
                        szoveg, varos.get(), cim.get()
                    )
                elif self.nezet == "Termek":
                    terem_mentese(
                        rekord.TeremID if rekord else None,
                        telephely_opciok[telephely_menu.get()],
                        szoveg, leiras.get()
                    )
                else:
                    magassag_szoveg = magassag.get().strip()
                    if magassag_szoveg and not magassag_szoveg.isdecimal():
                        raise ValueError("A rack magasságához pozitív egész számot adj meg.")
                    hely_mentese(
                        rekord.HelyID if rekord else None,
                        telephely_opciok[telephely_menu.get()],
                        terem_opciok[terem_menu.get()],
                        tipus_opciok[tipus_menu.get()],
                        szoveg, leiras.get(),
                        int(magassag_szoveg) if magassag_szoveg else None
                    )
            except Exception as hiba:
                messagebox.showerror("Mentési hiba", str(hiba), parent=ablak)
                return

            ablak.destroy()
            self.megjelenites()
            messagebox.showinfo("Siker", "Az adatok mentése megtörtént.", parent=self)

        muveleti_gomb(
            keret, text="Mentés", height=40, command=mentes
        ).pack(fill="x", pady=20)


from api import bekotes
bekotes(globals(), "infrastruktura")
