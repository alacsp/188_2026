"""Előre feltöltött és új törzsadatok kezelése."""


from adatbazis import tranzakcio, lekerdezes
from fiokok import jogosult
from felulet_seged import FelugroAblak, muveleti_gomb
import customtkinter as ctk
from tkinter import messagebox
from fiokok import probal, mezo


# Megadom a szerkeszthető mezőket, a hosszukat és a kötelezőséget.
TABLAK = {
    "Gyarto": {"Nev": (100, True)},
    "EszkozTipus": {"Nev": (100, True), "Leiras": (500, False)},
    "Modell": {"GyartoID": (int, True), "EszkozTipusID": (int, True),
               "Nev": (150, True), "MagassagU": (int, False)},
    "Statusz": {"Kod": (30, True), "Nev": (100, True), "Leiras": (500, False)},
    "HelyTipus": {"Kod": (30, True), "Nev": (100, True), "Leiras": (500, False)},
    "KarbantartasTipus": {"Kod": (30, True), "Nev": (100, True)},
    "GaranciaTipus": {"Kod": (30, True), "Nev": (100, True)},
    "KapcsolatTipus": {"Kod": (30, True), "Nev": (100, True)},
}


# A törzsadat-műveletek a táblák leírása alapján listáznak és mentenek.
def torzsadatok_listazasa(tabla):
    mezok = TABLAK[tabla]
    return lekerdezes(f"SELECT {tabla}ID,{','.join(mezok)},Aktiv FROM torzs.{tabla} ORDER BY Nev")


def torzsadat_mentese(tabla, az, adatok, aktiv):
    mezok = TABLAK[tabla]
    ertekek = []
    for nev, (tipus, kotelezo) in mezok.items():
        v = str(adatok.get(nev) if adatok.get(nev) is not None else "").strip()
        if not v:
            if kotelezo:
                raise ValueError(f"Kötelező mező: {nev}")
            ertekek.append(None)
        elif tipus is int:
            try:
                szam = int(v)
            except ValueError:
                raise ValueError(f"Egész szám szükséges: {nev}") from None
            if szam < 1 or (nev == "MagassagU" and szam > 255):
                raise ValueError(f"Érvénytelen érték: {nev}")
            ertekek.append(szam)
        else:
            if len(v) > tipus:
                raise ValueError(f"Túl hosszú mező: {nev} (legfeljebb {tipus})")
            ertekek.append(v)
    uj = dict(zip(mezok, ertekek))
    def mentes(k):
        jogosult(k, iras=True)
        if az is not None:
            k.execute(f"SELECT * FROM torzs.{tabla} WITH (UPDLOCK,HOLDLOCK) WHERE {tabla}ID=?", (az,))
            regi = k.fetchone()
            if regi is None:
                raise ValueError("A törzsadat már nem található.")
            # Megőrzöm a program és a riportok által használt technikai kódokat.
            if tabla in ("Statusz", "HelyTipus") and uj["Kod"] != regi.Kod:
                raise ValueError("A státusz/helytípus technikai kódja nem módosítható; a neve és leírása igen.")
        if tabla == "Modell":
            for szulo in ("Gyarto", "EszkozTipus"):
                k.execute(f"SELECT 1 FROM torzs.{szulo} WITH (HOLDLOCK) WHERE {szulo}ID=?", (uj[szulo+"ID"],))
                if k.fetchone() is None:
                    raise ValueError(f"Nem található: {szulo}")
            if az is not None:
                k.execute("SELECT e.EszkozID,e.HelyID,e.RackPozicioKezdet,r.MagassagU "
                          "FROM eszkoz.Eszkoz e WITH (UPDLOCK,HOLDLOCK) "
                          "LEFT JOIN infrastruktura.Rack r ON r.HelyID=e.HelyID "
                          "WHERE e.ModellID=? AND e.Aktiv=1 AND e.RackPozicioKezdet IS NOT NULL", (az,))
                helyek = k.fetchall()
                for e in helyek:
                    m = uj["MagassagU"]
                    if m is None or e.MagassagU is None or e.RackPozicioKezdet+m-1 > e.MagassagU:
                        raise ValueError("Az új modellmagasság nem fér el egy meglévő rackpozíción.")
                    k.execute("SELECT 1 FROM eszkoz.Eszkoz e WITH (UPDLOCK,HOLDLOCK) "
                              "JOIN torzs.Modell m ON m.ModellID=e.ModellID "
                              "WHERE e.HelyID=? AND e.EszkozID<>? AND e.Aktiv=1 "
                              "AND e.RackPozicioKezdet IS NOT NULL AND "
                              "(m.MagassagU IS NULL OR (e.RackPozicioKezdet<=? AND "
                              "e.RackPozicioKezdet+CASE WHEN e.ModellID=? THEN ? ELSE m.MagassagU END-1>=?))",
                              (e.HelyID,e.EszkozID,e.RackPozicioKezdet+m-1,az,m,e.RackPozicioKezdet))
                    if k.fetchone() is not None:
                        raise ValueError("Az új modellmagasság rackütközést okozna.")
        oszlopok = list(mezok) + ["Aktiv"]
        if az is None:
            k.execute(f"INSERT INTO torzs.{tabla} ({','.join(oszlopok)}) VALUES ({','.join('?' for _ in oszlopok)})",
                      (*ertekek, bool(aktiv)))
        else:
            k.execute(f"UPDATE torzs.{tabla} SET {','.join(c+'=?' for c in oszlopok)} WHERE {tabla}ID=?",
                      (*ertekek, bool(aktiv), az))
            if k.rowcount != 1:
                raise ValueError("Nem sikerült menteni a törzsadatot.")
    tranzakcio(mentes)



NEVEK = dict(zip(TABLAK, ("Gyártók", "Eszköztípusok", "Modellek", "Státuszok",
                          "Helytípusok", "Karbantartástípusok", "Garanciatípusok", "Kapcsolattípusok")))
MEZOK = {"Nev": "Név", "Kod": "Technikai kód", "Leiras": "Leírás",
         "GyartoID": "Gyártó", "EszkozTipusID": "Eszköztípus", "MagassagU": "Magasság (U)"}


# A törzsadat-felület a gyártók, modellek, állapotok és egyéb választólisták karbantartását végzi.
class TorzsadatFelulet(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.tabla = "Gyarto"
        ctk.CTkOptionMenu(self, values=list(NEVEK.values()), command=self.valaszt).pack(pady=10)
        muveleti_gomb(self, text="Új törzsadat", command=lambda: self.urlap()).pack(pady=5)
        self.sorok = ctk.CTkScrollableFrame(self)
        self.sorok.pack(fill="both", expand=True)
        probal(self, self.frissit)

    def valaszt(self, nev):
        self.tabla = next(k for k,v in NEVEK.items() if v == nev)
        probal(self, self.frissit)

    def frissit(self):
        adatok = torzsadatok_listazasa(self.tabla)
        for e in self.sorok.winfo_children():
            e.destroy()
        for s in adatok:
            r = ctk.CTkFrame(self.sorok)
            r.pack(fill="x", pady=3)
            ctk.CTkLabel(r, text=f"#{s[0]}  {s.Nev}  {'(inaktív)' if not s.Aktiv else ''}").pack(side="left", padx=10)
            muveleti_gomb(r, text="Szerkesztés", command=lambda sor=s: self.urlap(sor)).pack(side="right", padx=10)

    def urlap(self, sor=None):
        tabla = self.tabla
        w = FelugroAblak(self)
        w.title(NEVEK[tabla] + " – szerkesztés")
        w.geometry("620x650")
        w.transient(self.winfo_toplevel())
        w.grab_set()
        keret = ctk.CTkScrollableFrame(w)
        keret.pack(fill="both", expand=True, padx=15, pady=15)
        mezok, valasztok = {}, {}
        for nev in TABLAK[tabla]:
            if nev in ("GyartoID", "EszkozTipusID"):
                opciok = {f"#{s[0]} {s.Nev}": s[0] for s in torzsadatok_listazasa(nev[:-2])}
                if not opciok:
                    w.destroy()
                    messagebox.showwarning("Hiányzó adat", "Előbb adj meg gyártót és eszköztípust.", parent=self)
                    return
                ctk.CTkLabel(keret, text=MEZOK[nev]).pack()
                m = ctk.CTkOptionMenu(keret, values=list(opciok))
                m.pack(fill="x", padx=15)
                if sor:
                    m.set(next(k for k,v in opciok.items() if v == getattr(sor,nev)))
                valasztok[nev] = opciok
            else:
                m = mezo(keret, MEZOK[nev])
                if sor and getattr(sor,nev) is not None:
                    m.insert(0,str(getattr(sor,nev)))
                if sor and nev == "Kod" and tabla in ("Statusz", "HelyTipus"):
                    m.configure(state="disabled")
            mezok[nev] = m
        aktiv = ctk.BooleanVar(value=bool(sor.Aktiv) if sor else True)
        ctk.CTkCheckBox(keret, text="Aktív", variable=aktiv).pack(pady=15)
        def ment():
            adatok = {n: valasztok[n][m.get()] if n in valasztok else m.get() for n,m in mezok.items()}
            torzsadat_mentese(tabla, sor[0] if sor else None, adatok, aktiv.get())
            w.destroy()
            self.frissit()
        muveleti_gomb(keret, text="Mentés", command=lambda: probal(w, ment)).pack(pady=15)


from api import bekotes
bekotes(globals(), "torzsadatok")
