from ellenorzes import szoveg as _szoveg
"""Hálózati interfészek és IP-címek kezelése."""


import ipaddress
import re
from adatbazis import kapcsolat_letrehozasa, lekerdezes as _lista
from felulet_seged import FelugroAblak, muveleti_gomb
from tkinter import messagebox
import customtkinter as ctk


# A hálózati műveletek az eszközinterfészeket és azok IP-címeit kezelik.
def interfeszek_listazasa():
    return _lista("""
        SELECT h.HalozatiInterfeszID, h.EszkozID, e.LeltariSzam,
               h.Nev, h.MACCim, h.SebessegMbps, h.Megjegyzes, h.Aktiv,
               (SELECT COUNT(*) FROM halozat.IPCim AS i
                WHERE i.HalozatiInterfeszID = h.HalozatiInterfeszID
                  AND i.Aktiv = 1) AS AktivIPDb
        FROM halozat.HalozatiInterfesz AS h
        JOIN eszkoz.Eszkoz AS e ON h.EszkozID = e.EszkozID
        ORDER BY e.LeltariSzam, h.Nev, h.HalozatiInterfeszID
    """)


def ip_cimek_listazasa():
    return _lista("""
        SELECT i.IPCimID, i.HalozatiInterfeszID, i.IPCim, i.PrefixHossz,
               i.Elsodleges, i.Aktiv, i.Megjegyzes,
               h.Nev AS InterfeszNev, h.Aktiv AS InterfeszAktiv,
               e.LeltariSzam
        FROM halozat.IPCim AS i
        JOIN halozat.HalozatiInterfesz AS h
            ON i.HalozatiInterfeszID = h.HalozatiInterfeszID
        JOIN eszkoz.Eszkoz AS e ON h.EszkozID = e.EszkozID
        ORDER BY e.LeltariSzam, h.Nev, i.IPCimID
    """)


def interfesz_eszkozok(kivalasztott_id=None):
    return _lista("""
        SELECT EszkozID, LeltariSzam, Aktiv FROM eszkoz.Eszkoz
        WHERE Aktiv = 1 OR EszkozID = ? ORDER BY LeltariSzam
    """, (kivalasztott_id,))


def ip_interfeszek(kivalasztott_id=None):
    return _lista("""
        SELECT h.HalozatiInterfeszID, h.Nev, h.Aktiv,
               e.LeltariSzam, e.Aktiv AS EszkozAktiv
        FROM halozat.HalozatiInterfesz AS h
        JOIN eszkoz.Eszkoz AS e ON h.EszkozID = e.EszkozID
        WHERE (h.Aktiv = 1 AND e.Aktiv = 1)
           OR h.HalozatiInterfeszID = ?
        ORDER BY e.LeltariSzam, h.Nev, h.HalozatiInterfeszID
    """, (kivalasztott_id,))




def _mac(ertek):
    szoveg = (ertek or "").strip().upper().replace("-", ":")
    if not szoveg:
        return None
    if not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", szoveg):
        raise ValueError("A MAC-cím formátuma például AA:BB:CC:DD:EE:FF.")
    return szoveg


def _sebesseg(ertek):
    szoveg = str("" if ertek is None else ertek).strip()
    if not szoveg:
        return None
    try:
        sebesseg = int(szoveg)
    except ValueError as hiba:
        raise ValueError("A sebesség egész szám legyen (Mbps).") from hiba
    if not 1 <= sebesseg <= 2147483647:
        raise ValueError("A sebesség pozitív, legfeljebb 2147483647 lehet.")
    return sebesseg


def interfesz_mentese(azonosito, eszkoz_id, nev, mac, sebesseg, megjegyzes):
    if eszkoz_id is None:
        raise ValueError("Eszközt kötelező kiválasztani.")
    nev = _szoveg(nev, 100, "interfész neve")
    mac = _mac(mac)
    sebesseg = _sebesseg(sebesseg)
    megjegyzes = _szoveg(megjegyzes, 500, "megjegyzés")
    kapcsolat = kapcsolat_letrehozasa()
    try:
        kurzor = kapcsolat.cursor()
        from fiokok import jogosult
        jogosult(kurzor, iras=True)
        regi_eszkoz = None
        if azonosito is not None:
            kurzor.execute("""
                SELECT EszkozID FROM halozat.HalozatiInterfesz
                WHERE HalozatiInterfeszID = ? AND Aktiv = 1
            """, (azonosito,))
            regi = kurzor.fetchone()
            if regi is None:
                raise ValueError("Az aktív interfész nem található.")
            regi_eszkoz = regi.EszkozID

        # Az érintett eszközöket azonos sorrendben zárolom.
        for az in sorted({eszkoz_id, regi_eszkoz} - {None}):
            kurzor.execute("""
                SELECT Aktiv FROM eszkoz.Eszkoz WITH (UPDLOCK, HOLDLOCK)
                WHERE EszkozID = ?
            """, (az,))
            tulajdonos = kurzor.fetchone()
            if tulajdonos is None or (az == eszkoz_id and not tulajdonos.Aktiv):
                raise ValueError("A kiválasztott eszköz nem aktív vagy nem található.")

        if azonosito is not None:
            kurzor.execute("""
                SELECT EszkozID FROM halozat.HalozatiInterfesz WITH (UPDLOCK, HOLDLOCK)
                WHERE HalozatiInterfeszID = ? AND Aktiv = 1
            """, (azonosito,))
            ujra = kurzor.fetchone()
            if ujra is None or ujra.EszkozID != regi_eszkoz:
                raise ValueError("Az interfész tulajdonosa közben megváltozott. Frissítsd a listát.")
        ertekek = (eszkoz_id, nev, mac, sebesseg, megjegyzes)
        if azonosito is None:
            kurzor.execute("""
                INSERT INTO halozat.HalozatiInterfesz
                    (EszkozID, Nev, MACCim, SebessegMbps, Megjegyzes)
                VALUES (?, ?, ?, ?, ?)
            """, ertekek)
        else:
            kurzor.execute("""
                UPDATE halozat.HalozatiInterfesz
                SET EszkozID = ?, Nev = ?, MACCim = ?,
                    SebessegMbps = ?, Megjegyzes = ?
                WHERE HalozatiInterfeszID = ? AND Aktiv = 1
            """, (*ertekek, azonosito))
            if kurzor.rowcount != 1:
                raise ValueError("Az interfész módosítása nem sikerült.")
        kapcsolat.commit()
    except Exception:
        kapcsolat.rollback()
        raise
    finally:
        kapcsolat.close()


def interfesz_aktivitas(azonosito, aktiv):
    kapcsolat = kapcsolat_letrehozasa()
    try:
        kurzor = kapcsolat.cursor()
        from fiokok import jogosult
        jogosult(kurzor, iras=True)
        kurzor.execute("""
            SELECT EszkozID FROM halozat.HalozatiInterfesz
            WHERE HalozatiInterfeszID = ?
        """, (azonosito,))
        rekord = kurzor.fetchone()
        if rekord is None:
            raise ValueError("Az interfész nem található.")
        eszkoz_id = rekord.EszkozID
        kurzor.execute("""
            SELECT Aktiv FROM eszkoz.Eszkoz WITH (UPDLOCK, HOLDLOCK)
            WHERE EszkozID = ?
        """, (eszkoz_id,))
        eszkoz = kurzor.fetchone()
        kurzor.execute("""
            SELECT Aktiv FROM halozat.HalozatiInterfesz WITH (UPDLOCK, HOLDLOCK)
            WHERE HalozatiInterfeszID = ? AND EszkozID = ?
        """, (azonosito, eszkoz_id))
        rekord = kurzor.fetchone()
        if rekord is None or bool(rekord.Aktiv) == bool(aktiv):
            raise ValueError("Az interfész nem található vagy már ebben az állapotban van.")
        if aktiv and (eszkoz is None or not eszkoz.Aktiv):
            raise ValueError("Inaktív eszközhöz nem állítható vissza az interfész.")
        if not aktiv:
            kurzor.execute("""
                SELECT COUNT(*) FROM halozat.IPCim
                WHERE HalozatiInterfeszID = ? AND Aktiv = 1
            """, (azonosito,))
            if kurzor.fetchone()[0]:
                raise ValueError("Előbb inaktiváld az interfész aktív IP-címeit.")
        kurzor.execute("""
            UPDATE halozat.HalozatiInterfesz SET Aktiv = ?
            WHERE HalozatiInterfeszID = ?
        """, (int(aktiv), azonosito))
        kapcsolat.commit()
    except Exception:
        kapcsolat.rollback()
        raise
    finally:
        kapcsolat.close()


# Az IP-cím és a prefix ellenőrzése az ipaddress szabályai szerint történik.
def _ip_es_prefix(cim, prefix):
    try:
        ip = ipaddress.ip_address(str(cim).strip())
    except ValueError as hiba:
        raise ValueError("Érvényes IPv4- vagy IPv6-címet adj meg.") from hiba
    szoveg = str("" if prefix is None else prefix).strip()
    if not szoveg:
        return str(ip), None
    try:
        hossz = int(szoveg)
    except ValueError as hiba:
        raise ValueError("A prefixhossz egész szám legyen.") from hiba
    maximum = 32 if ip.version == 4 else 128
    if not 0 <= hossz <= maximum:
        raise ValueError(f"IPv{ip.version} esetén a prefixhossz 0 és {maximum} közötti lehet.")
    return str(ip), hossz


def ip_mentese(azonosito, interfesz_id, cim, prefix, elsodleges, megjegyzes):
    if interfesz_id is None:
        raise ValueError("Interfészt kötelező kiválasztani.")
    cim, prefix = _ip_es_prefix(cim, prefix)
    megjegyzes = _szoveg(megjegyzes, 500, "megjegyzés")
    kapcsolat = kapcsolat_letrehozasa()
    try:
        kurzor = kapcsolat.cursor()
        from fiokok import jogosult
        jogosult(kurzor, iras=True)
        # Zárolom az interfészt az egyidejű módosítások ellen.
        kurzor.execute("""
            SELECT h.Aktiv, e.Aktiv AS EszkozAktiv
            FROM halozat.HalozatiInterfesz AS h WITH (UPDLOCK, HOLDLOCK)
            JOIN eszkoz.Eszkoz AS e ON h.EszkozID = e.EszkozID
            WHERE h.HalozatiInterfeszID = ?
        """, (interfesz_id,))
        interfesz = kurzor.fetchone()
        if (interfesz is None or not interfesz.Aktiv or
                not interfesz.EszkozAktiv):
            raise ValueError("Az interfész vagy a hozzá tartozó eszköz inaktív.")
        if azonosito is not None:
            kurzor.execute("""
                SELECT 1 FROM halozat.IPCim
                WHERE IPCimID = ? AND Aktiv = 1
            """, (azonosito,))
            if kurzor.fetchone() is None:
                raise ValueError("Az aktív IP-cím nem található.")
        if elsodleges:
            kurzor.execute("""
                SELECT COUNT(*) FROM halozat.IPCim
                WHERE HalozatiInterfeszID = ? AND Elsodleges = 1
                  AND Aktiv = 1 AND IPCimID <> ?
            """, (interfesz_id, azonosito or 0))
            if kurzor.fetchone()[0]:
                raise ValueError("Ennek az interfésznek már van aktív elsődleges IP-címe.")
        ertekek = (interfesz_id, cim, prefix, int(elsodleges), megjegyzes)
        if azonosito is None:
            kurzor.execute("""
                INSERT INTO halozat.IPCim
                    (HalozatiInterfeszID, IPCim, PrefixHossz, Elsodleges, Megjegyzes)
                VALUES (?, ?, ?, ?, ?)
            """, ertekek)
        else:
            kurzor.execute("""
                UPDATE halozat.IPCim
                SET HalozatiInterfeszID = ?, IPCim = ?, PrefixHossz = ?,
                    Elsodleges = ?, Megjegyzes = ?
                WHERE IPCimID = ? AND Aktiv = 1
            """, (*ertekek, azonosito))
            if kurzor.rowcount != 1:
                raise ValueError("Az IP-cím módosítása nem sikerült.")
        kapcsolat.commit()
    except Exception:
        kapcsolat.rollback()
        raise
    finally:
        kapcsolat.close()


def ip_aktivitas(azonosito, aktiv):
    kapcsolat = kapcsolat_letrehozasa()
    try:
        kurzor = kapcsolat.cursor()
        from fiokok import jogosult
        jogosult(kurzor, iras=True)
        # Megkeresem és zárolom a kapcsolódó interfészt.
        kurzor.execute("""
            SELECT HalozatiInterfeszID FROM halozat.IPCim WHERE IPCimID = ?
        """, (azonosito,))
        sor = kurzor.fetchone()
        if sor is None:
            raise ValueError("Az IP-cím nem található.")
        interfesz_id = sor.HalozatiInterfeszID
        kurzor.execute("""
            SELECT h.Aktiv, e.Aktiv AS EszkozAktiv
            FROM halozat.HalozatiInterfesz AS h WITH (UPDLOCK, HOLDLOCK)
            JOIN eszkoz.Eszkoz AS e ON h.EszkozID = e.EszkozID
            WHERE h.HalozatiInterfeszID = ?
        """, (interfesz_id,))
        szulo = kurzor.fetchone()
        kurzor.execute("""
            SELECT Aktiv, Elsodleges FROM halozat.IPCim WITH (UPDLOCK)
            WHERE IPCimID = ? AND HalozatiInterfeszID = ?
        """, (azonosito, interfesz_id))
        rekord = kurzor.fetchone()
        if rekord is None or bool(rekord.Aktiv) == bool(aktiv):
            raise ValueError("Az IP-cím már ebben az állapotban van.")
        if aktiv:
            if not szulo or not szulo.Aktiv or not szulo.EszkozAktiv:
                raise ValueError("Az interfész és az eszköz legyen aktív.")
            if rekord.Elsodleges:
                kurzor.execute("""
                    SELECT COUNT(*) FROM halozat.IPCim
                    WHERE HalozatiInterfeszID = ? AND Elsodleges = 1
                      AND Aktiv = 1 AND IPCimID <> ?
                """, (interfesz_id, azonosito))
                if kurzor.fetchone()[0]:
                    raise ValueError("Másik aktív elsődleges IP-cím már létezik.")
        kurzor.execute("""
            UPDATE halozat.IPCim SET Aktiv = ? WHERE IPCimID = ?
        """, (int(aktiv), azonosito))
        kapcsolat.commit()
    except Exception:
        kapcsolat.rollback()
        raise
    finally:
        kapcsolat.close()



# A felület külön nézetet biztosít az interfészek és az IP-címek kezeléséhez.
class HalozatFelulet(ctk.CTkFrame):
    def __init__(self, szulo):
        super().__init__(szulo, fg_color="transparent")
        self.nezet = "Interfészek"
        self.allapot = "Aktív"
        self.keresett = ""
        self.megjelenites()

    def nezet_valtas(self, ertek):
        self.nezet = ertek
        self.keresett = ""
        self.megjelenites()

    def allapot_valtas(self, ertek):
        self.allapot = ertek
        self.megjelenites()

    def alaphelyzet(self):
        self.keresett = ""
        self.megjelenites()

    def megjelenites(self):
        for elem in self.winfo_children():
            elem.destroy()
        try:
            adatok = (interfeszek_listazasa() if self.nezet == "Interfészek"
                      else ip_cimek_listazasa())
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba), parent=self)
            return
        gombsor = ctk.CTkFrame(self, fg_color="transparent")
        gombsor.pack(fill="x", padx=10, pady=10)
        valto = ctk.CTkSegmentedButton(gombsor, values=["Interfészek", "IP-címek"],
                                       command=self.nezet_valtas)
        valto.pack(side="left", padx=5)
        valto.set(self.nezet)
        szuro = ctk.CTkSegmentedButton(gombsor, values=["Aktív", "Inaktív"],
                                       command=self.allapot_valtas)
        szuro.pack(side="left", padx=10)
        szuro.set(self.allapot)
        muveleti_gomb(
            gombsor, text="+ Új interfész" if self.nezet == "Interfészek" else "+ Új IP-cím",
            width=125, command=self.interfesz_urlap if self.nezet == "Interfészek"
            else self.ip_urlap
        ).pack(side="left", padx=5)

        keretosor = ctk.CTkFrame(self, fg_color="transparent")
        keretosor.pack(fill="x", padx=10, pady=(0, 7))
        kereso = ctk.CTkEntry(keretosor, width=225, placeholder_text="Keresés...")
        kereso.pack(side="left", padx=5)
        kereso.insert(0, self.keresett)

        def kereses():
            self.keresett = kereso.get().strip()
            self.megjelenites()

        ctk.CTkButton(keretosor, text="Keresés", width=85,
                      command=kereses).pack(side="left", padx=5)
        kereso.bind("<Return>", lambda _e: kereses())
        ctk.CTkButton(keretosor, text="Alaphelyzet", width=100,
                      command=self.alaphelyzet).pack(side="left", padx=5)

        sorok = [r for r in adatok if bool(r.Aktiv) == (self.allapot == "Aktív")]
        if self.keresett:
            keresett = self.keresett.casefold()
            if self.nezet == "Interfészek":
                sorok = [r for r in sorok if any(
                    keresett in str(v or "").casefold()
                    for v in (r.LeltariSzam, r.Nev, r.MACCim, r.Megjegyzes))]
            else:
                sorok = [r for r in sorok if any(
                    keresett in str(v or "").casefold()
                    for v in (r.LeltariSzam, r.InterfeszNev, r.IPCim, r.Megjegyzes))]
        ctk.CTkLabel(self, text=f"Találatok: {len(sorok)} / {len(adatok)}",
                     anchor="w").pack(fill="x", padx=15, pady=5)
        if self.nezet == "Interfészek":
            fejlecek = ("Eszköz", "Interfész", "MAC-cím", "Mbps", "Aktív IP-k", "Műveletek")
            meretek = (110, 140, 155, 85, 90, 205)
        else:
            fejlecek = ("Eszköz", "Interfész", "IP-cím", "Prefix", "Elsődleges", "Műveletek")
            meretek = (110, 140, 190, 70, 105, 205)
        tabla = ctk.CTkScrollableFrame(self)
        tabla.pack(fill="both", expand=True, padx=10, pady=5)
        for oszlop, nev in enumerate(fejlecek):
            ctk.CTkLabel(tabla, text=nev, width=meretek[oszlop], anchor="w",
                         font=ctk.CTkFont(weight="bold")
                         ).grid(row=0, column=oszlop, padx=5, pady=8, sticky="w")
        for index, r in enumerate(sorok, start=1):
            if self.nezet == "Interfészek":
                ertekek = (r.LeltariSzam, r.Nev or "–", r.MACCim or "–",
                           r.SebessegMbps or "–", r.AktivIPDb)
            else:
                ertekek = (r.LeltariSzam, r.InterfeszNev or "–", r.IPCim,
                           r.PrefixHossz if r.PrefixHossz is not None else "–",
                           "Igen" if r.Elsodleges else "Nem")
            for oszlop, ertek in enumerate(ertekek):
                ctk.CTkLabel(tabla, text=str(ertek), width=meretek[oszlop],
                             anchor="w", wraplength=meretek[oszlop]
                             ).grid(row=index, column=oszlop, padx=5, pady=5, sticky="w")
            gombok = ctk.CTkFrame(tabla, fg_color="transparent")
            gombok.grid(row=index, column=5, padx=5, pady=5)
            if r.Aktiv:
                szerkesztes = self.interfesz_urlap if self.nezet == "Interfészek" else self.ip_urlap
                muveleti_gomb(gombok, text="Szerkesztés", width=90,
                              command=lambda rekord=r, muvelet=szerkesztes: muvelet(rekord)
                              ).pack(side="left", padx=2)
            muveleti_gomb(
                gombok, text="Inaktiválás" if r.Aktiv else "Visszaállítás",
                width=105, command=lambda rekord=r: self.aktivitas(rekord)
            ).pack(side="left", padx=2)
        if not sorok:
            ctk.CTkLabel(tabla, text="Nincs megjeleníthető rekord.").grid(
                row=1, column=0, columnspan=6, pady=25)

    def aktivitas(self, rekord):
        uj_aktiv = not bool(rekord.Aktiv)
        muvelet = "visszaállítod" if uj_aktiv else "inaktiválod"
        if not messagebox.askyesno("Megerősítés",
                                   f"Biztosan {muvelet} a kiválasztott rekordot?",
                                   parent=self):
            return
        try:
            if self.nezet == "Interfészek":
                interfesz_aktivitas(rekord.HalozatiInterfeszID, uj_aktiv)
            else:
                ip_aktivitas(rekord.IPCimID, uj_aktiv)
            self.megjelenites()
        except Exception as hiba:
            messagebox.showerror("Műveleti hiba", str(hiba), parent=self)

    @staticmethod
    def mezo(keret, felirat, ertek=""):
        ctk.CTkLabel(keret, text=felirat, anchor="w").pack(fill="x", pady=(12, 4))
        mezo = ctk.CTkEntry(keret)
        mezo.pack(fill="x")
        mezo.insert(0, str("" if ertek is None else ertek))
        return mezo

    @staticmethod
    def valaszto(keret, felirat, opciok, azonosito=None):
        ctk.CTkLabel(keret, text=felirat, anchor="w").pack(fill="x", pady=(12, 4))
        menu = ctk.CTkOptionMenu(keret, values=list(opciok))
        menu.pack(fill="x")
        menu.set(next((n for n, i in opciok.items() if i == azonosito),
                      next(iter(opciok))))
        return menu

    def _ablak(self, cim):
        ablak = FelugroAblak(self)
        ablak.title(cim)
        ablak.geometry("750x680")
        ablak.minsize(660, 550)
        ablak.transient(self.winfo_toplevel())
        keret = ctk.CTkScrollableFrame(ablak)
        keret.pack(fill="both", expand=True, padx=20, pady=20)
        ablak.grab_set()
        return ablak, keret

    def interfesz_urlap(self, rekord=None):
        try:
            eszkozok = interfesz_eszkozok(rekord.EszkozID if rekord else None)
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba), parent=self)
            return
        if not eszkozok:
            messagebox.showwarning("Hiányzó eszköz", "Nincs választható eszköz.", parent=self)
            return
        opciok = {f"{e.LeltariSzam} (ID: {e.EszkozID})": e.EszkozID for e in eszkozok}
        ablak, keret = self._ablak("Interfész szerkesztése" if rekord else "Új interfész")
        eszkoz = self.valaszto(keret, "Eszköz *", opciok,
                              rekord.EszkozID if rekord else None)
        nev = self.mezo(keret, "Interfész neve (pl. eth0)", rekord.Nev if rekord else "")
        mac = self.mezo(keret, "MAC-cím (AA:BB:CC:DD:EE:FF)",
                        rekord.MACCim if rekord else "")
        sebesseg = self.mezo(keret, "Sebesség (Mbps)",
                             rekord.SebessegMbps if rekord else "")
        ctk.CTkLabel(keret, text="Megjegyzés", anchor="w").pack(
            fill="x", pady=(12, 4))
        megjegyzes = ctk.CTkTextbox(keret, height=85)
        megjegyzes.pack(fill="x")
        megjegyzes.insert("1.0", (rekord.Megjegyzes or "") if rekord else "")

        def mentes():
            try:
                interfesz_mentese(
                    rekord.HalozatiInterfeszID if rekord else None,
                    opciok[eszkoz.get()], nev.get(), mac.get(),
                    sebesseg.get(), megjegyzes.get("1.0", "end").strip())
            except Exception as hiba:
                messagebox.showerror("Mentési hiba", str(hiba), parent=ablak)
                return
            ablak.destroy()
            self.megjelenites()
            messagebox.showinfo("Siker", "Az interfész mentve.", parent=self)

        muveleti_gomb(keret, text="Mentés", height=40,
                      command=mentes).pack(fill="x", pady=20)

    def ip_urlap(self, rekord=None):
        try:
            interfeszek = ip_interfeszek(rekord.HalozatiInterfeszID if rekord else None)
        except Exception as hiba:
            messagebox.showerror("Adatbázishiba", str(hiba), parent=self)
            return
        if not interfeszek:
            messagebox.showwarning("Hiányzó interfész",
                                   "Előbb rögzíts egy aktív interfészt.", parent=self)
            return
        opciok = {
            f"{r.LeltariSzam} / {r.Nev or 'Névtelen'} (ID: {r.HalozatiInterfeszID})":
            r.HalozatiInterfeszID for r in interfeszek
        }
        ablak, keret = self._ablak("IP-cím szerkesztése" if rekord else "Új IP-cím")
        interfesz = self.valaszto(keret, "Hálózati interfész *", opciok,
                                 rekord.HalozatiInterfeszID if rekord else None)
        cim = self.mezo(keret, "IP-cím * (IPv4 vagy IPv6)",
                        rekord.IPCim if rekord else "")
        prefix = self.mezo(keret, "Prefixhossz (IPv4: 0–32, IPv6: 0–128)",
                           rekord.PrefixHossz if rekord and rekord.PrefixHossz is not None else "")
        elsodleges = ctk.CTkCheckBox(keret, text="Elsődleges IP-cím")
        elsodleges.pack(anchor="w", pady=(18, 8))
        if rekord and rekord.Elsodleges:
            elsodleges.select()
        ctk.CTkLabel(keret, text="Megjegyzés", anchor="w").pack(
            fill="x", pady=(12, 4))
        megjegyzes = ctk.CTkTextbox(keret, height=90)
        megjegyzes.pack(fill="x")
        megjegyzes.insert("1.0", (rekord.Megjegyzes or "") if rekord else "")

        def mentes():
            try:
                ip_mentese(
                    rekord.IPCimID if rekord else None,
                    opciok[interfesz.get()], cim.get(), prefix.get(),
                    bool(elsodleges.get()),
                    megjegyzes.get("1.0", "end").strip())
            except Exception as hiba:
                messagebox.showerror("Mentési hiba", str(hiba), parent=ablak)
                return
            ablak.destroy()
            self.megjelenites()
            messagebox.showinfo("Siker", "Az IP-cím mentve.", parent=self)

        muveleti_gomb(keret, text="Mentés", height=40,
                      command=mentes).pack(fill="x", pady=20)


from api import bekotes
bekotes(globals(), "halozat")
