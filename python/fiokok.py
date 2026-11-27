"""Belépés, jelszavak és felhasználói fiókok kezelése."""


import hashlib
import hmac
import secrets
from dataclasses import dataclass
from functools import partial
import adatbazis
from felulet_seged import FelugroAblak
import customtkinter as ctk
from tkinter import messagebox


lekerdezes = partial(adatbazis.lekerdezes, vedett=False)
tranzakcio = partial(adatbazis.tranzakcio, vedett=False)


# A jelszó véletlen sóval és scrypt algoritmussal kerül tárolásra.
def jelszo_hash(jelszo):
    if not isinstance(jelszo, str) or not 12 <= len(jelszo) <= 256:
        raise ValueError("A jelszó hossza 12–256 karakter legyen.")
    so = secrets.token_bytes(16)
    kulcs = hashlib.scrypt(jelszo.encode(), salt=so, n=16384, r=8, p=1)
    return f"scrypt${so.hex()}${kulcs.hex()}"


def jelszo_egyezik(jelszo, tarolt):
    try:
        if not isinstance(jelszo, str) or len(jelszo) > 256:
            return False
        modszer, so, vart = tarolt.split("$")
        if modszer != "scrypt":
            return False
        kapott = hashlib.scrypt(jelszo.encode(), salt=bytes.fromhex(so), n=16384, r=8, p=1)
        return hmac.compare_digest(kapott.hex(), vart)
    except (ValueError, TypeError):
        return False


@dataclass(frozen=True)
class Munkamenet:
    az: int
    verzio: int


_munkamenet = None
_ures_hash = jelszo_hash(secrets.token_urlsafe(24))


def kilepes():
    global _munkamenet
    _munkamenet = None


# A munkamenet, a szerepkör és az írási jogosultság ellenőrzése minden védett művelet előtt.
def jogosult(k, admin=False, iras=False):
    if _munkamenet is None:
        raise PermissionError("Előbb jelentkezz be.")
    k.execute("SELECT Nev, Admin, Megtekinto FROM biztonsag.Felhasznalo WITH (UPDLOCK, HOLDLOCK) "
              "WHERE FelhasznaloID=? AND Verzio=? AND Aktiv=1",
              (_munkamenet.az, _munkamenet.verzio))
    sor = k.fetchone()
    if sor is None or (admin and not sor.Admin):
        raise PermissionError("A munkamenet lejárt, vagy nincs megfelelő jogosultság.")
    if iras and sor.Megtekinto:
        raise PermissionError("Megtekintőként a nyilvántartásokat nem módosíthatod.")
    return sor


def aktualis():
    return tranzakcio(lambda k: jogosult(k))


def van_fiok():
    return lekerdezes("SELECT TOP 1 FelhasznaloID FROM biztonsag.Felhasznalo", egy=True) is not None


def _nev(nev):
    nev = nev.strip()
    if not 1 <= len(nev) <= 100:
        raise ValueError("A felhasználónév 1–100 karakter legyen.")
    return nev


def letrehozas(nev, jelszo, admin=False, elso=False, megtekinto=False):
    if (admin or elso) and megtekinto:
        raise ValueError("Egy fiókhoz egy szerepkör választható.")
    nev, tarolt = _nev(nev), jelszo_hash(jelszo)
    def ment(k):
        # Zárolással biztosítom, hogy csak egy első adminisztrátor jöjjön létre.
        k.execute("SELECT FelhasznaloID FROM biztonsag.Felhasznalo WITH (UPDLOCK, HOLDLOCK)")
        sorok = k.fetchall()
        if elso:
            if sorok:
                raise PermissionError("Az első adminisztrátor már létrejött.")
        else:
            jogosult(k, admin=True)
        k.execute("INSERT INTO biztonsag.Felhasznalo (Nev,JelszoHash,Admin,Megtekinto) VALUES (?,?,?,?)",
                  (nev, tarolt, bool(admin or elso), bool(megtekinto)))
    tranzakcio(ment)


def belepes(nev, jelszo):
    global _munkamenet
    kilepes()
    def ellenoriz(k):
        k.execute("SELECT *, CASE WHEN Zarolva > SYSUTCDATETIME() THEN 1 ELSE 0 END AS Zart "
                  "FROM biztonsag.Felhasznalo WITH (UPDLOCK,HOLDLOCK) WHERE Nev=?", (nev.strip(),))
        sor = k.fetchone()
        helyes = jelszo_egyezik(jelszo, sor.JelszoHash if sor else _ures_hash)
        if sor is None or not sor.Aktiv or sor.Zart:
            return None
        if not helyes:
            k.execute("UPDATE biztonsag.Felhasznalo SET Hibak=Hibak+1, "
                      "Zarolva=CASE WHEN Hibak+1>=5 THEN DATEADD(MINUTE,15,SYSUTCDATETIME()) ELSE NULL END "
                      "WHERE FelhasznaloID=?", (sor.FelhasznaloID,))
            return None
        k.execute("UPDATE biztonsag.Felhasznalo SET Hibak=0,Zarolva=NULL WHERE FelhasznaloID=?", (sor.FelhasznaloID,))
        return Munkamenet(sor.FelhasznaloID, sor.Verzio)
    eredmeny = tranzakcio(ellenoriz)
    if eredmeny is None:
        raise ValueError("Hibás belépési adatok, inaktív vagy ideiglenesen zárolt fiók.")
    _munkamenet = eredmeny


def lista():
    def olvas(k):
        jogosult(k, True)
        k.execute("SELECT FelhasznaloID,Nev,Admin,Aktiv,Megtekinto FROM biztonsag.Felhasznalo ORDER BY Nev")
        return k.fetchall()
    return tranzakcio(olvas)


def fiok_modositasa(az, admin, aktiv, megtekinto=False):
    if admin and megtekinto:
        raise ValueError("Egy fiókhoz egy szerepkör választható.")
    def ment(k):
        # A fiókokat mindig azonos sorrendben zárolom.
        k.execute("SELECT FelhasznaloID,Admin,Aktiv FROM biztonsag.Felhasznalo WITH (UPDLOCK,HOLDLOCK)")
        sorok = k.fetchall()
        jogosult(k, True)
        cel = next((s for s in sorok if s.FelhasznaloID == az), None)
        if cel is None:
            raise ValueError("A fiók nem található.")
        if cel.Admin and cel.Aktiv and not (admin and aktiv):
            if sum(bool(s.Admin and s.Aktiv) for s in sorok) <= 1:
                raise ValueError("Az utolsó aktív adminisztrátor nem tiltható le.")
        k.execute("UPDATE biztonsag.Felhasznalo SET Admin=?,Aktiv=?,Megtekinto=?,Verzio=Verzio+1 WHERE FelhasznaloID=?",
                  (bool(admin), bool(aktiv), bool(megtekinto), az))
    tranzakcio(ment)


def reset_kiadasa(az):
    kod = secrets.token_urlsafe(32)
    def ment(k):
        jogosult(k, True)
        k.execute("UPDATE biztonsag.Felhasznalo SET ResetHash=?, "
                  "ResetLejar=DATEADD(MINUTE,30,SYSUTCDATETIME()),Verzio=Verzio+1 "
                  "WHERE FelhasznaloID=? AND Aktiv=1",
                  (hashlib.sha256(kod.encode()).hexdigest(), az))
        if k.rowcount != 1:
            raise ValueError("Nincs ilyen aktív fiók.")
    tranzakcio(ment)
    return kod


def jelszo_visszaallitas(nev, kod, uj):
    tarolt = jelszo_hash(uj)
    def ment(k):
        k.execute("UPDATE biztonsag.Felhasznalo SET JelszoHash=?, ResetHash=NULL,ResetLejar=NULL, "
                  "Hibak=0,Zarolva=NULL,Verzio=Verzio+1 WHERE Nev=? AND ResetHash=? "
                  "AND ResetLejar>SYSUTCDATETIME() AND Aktiv=1",
                  (tarolt, nev.strip(), hashlib.sha256(kod.encode()).hexdigest()))
        if k.rowcount != 1:
            raise ValueError("Érvénytelen vagy lejárt visszaállító kód.")
    tranzakcio(ment)


def jelszo_csere(regi, uj):
    global _munkamenet
    tarolt = jelszo_hash(uj)
    def ment(k):
        jogosult(k)
        k.execute("SELECT JelszoHash FROM biztonsag.Felhasznalo WHERE FelhasznaloID=?", (_munkamenet.az,))
        if not jelszo_egyezik(regi, k.fetchone().JelszoHash):
            raise ValueError("A jelenlegi jelszó hibás.")
        k.execute("UPDATE biztonsag.Felhasznalo SET JelszoHash=?,Verzio=Verzio+1,ResetHash=NULL,ResetLejar=NULL "
                  "WHERE FelhasznaloID=?", (tarolt, _munkamenet.az))
        return Munkamenet(_munkamenet.az, _munkamenet.verzio+1)
    _munkamenet = tranzakcio(ment)




def idozitok_leallitasa(ablak):
    for az in ablak.tk.call("after", "info"):
        # Csak az időzítést állítom le; a belső parancs törlését a widgetre hagyom.
        ablak.tk.call("after", "cancel", az)


def mezo(keret, felirat, titkos=False):
    ctk.CTkLabel(keret, text=felirat).pack(anchor="w", padx=15, pady=(8, 0))
    e = ctk.CTkEntry(keret, show="•" if titkos else "", width=360)
    e.pack(fill="x", padx=15, pady=4)
    return e


def probal(ablak, muvelet):
    try:
        muvelet()
    except Exception as h:
        messagebox.showerror("A művelet nem sikerült", str(h), parent=ablak)


# A bejelentkezési ablak hitelesíti a felhasználót, és kezeli a jelszó-visszaállítást.
class Belepes(ctk.CTk):
    def destroy(self):
        idozitok_leallitasa(self)
        super().destroy()

    def __init__(self):
        super().__init__()
        self.title("Eszköznyilvántartás – Bejelentkezés")
        self.geometry("500x620")
        self.siker = False
        try:
            self.elso = not van_fiok()
        except Exception as h:
            messagebox.showerror("A kiszolgáló nem elérhető",
                f"Előbb indítsd el a szerver_inditas.cmd fájlt, majd próbáld újra.\n\n{h}", parent=self)
            self.after(0, self.destroy)
            return
        if self.elso:
            messagebox.showinfo("Első adminisztrátor",
                "Az első adminfiókot a kiszolgáló gépén kell létrehozni.\n"
                "Indítsd a szerver_inditas.cmd --elso-admin parancsot.", parent=self)
            self.after(0,self.destroy)
            return
        ctk.CTkLabel(self, text="Első adminisztrátor létrehozása" if self.elso else "Bejelentkezés",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=20)
        self.nev = mezo(self, "Felhasználónév")
        self.jelszo = mezo(self, "Jelszó (új fióknál legalább 12 karakter)", True)
        self.ismet = mezo(self, "Jelszó újra", True) if self.elso else None
        ctk.CTkButton(self, text="Létrehozás és belépés" if self.elso else "Belépés",
                     command=lambda: probal(self, self.belep)).pack(pady=20)
        if not self.elso:
            ctk.CTkButton(self, text="Jelszó visszaállítása kóddal",
                         command=self.visszaallitas).pack(pady=8)
        self.bind("<Return>", lambda e: probal(self, self.belep))

    def belep(self):
        try:
            if self.elso:
                if self.jelszo.get() != self.ismet.get():
                    raise ValueError("A két jelszó eltér.")
                letrehozas(self.nev.get(), self.jelszo.get(), elso=True)
                self.elso = False
            belepes(self.nev.get(), self.jelszo.get())
            self.siker = True
            self.destroy()
        finally:
            if not self.siker:
                self.jelszo.delete(0, "end")

    def visszaallitas(self):
        w = FelugroAblak(self)
        w.title("Jelszó visszaállítása")
        w.geometry("500x530")
        w.transient(self)
        w.grab_set()
        nev = mezo(w, "Felhasználónév")
        kod = mezo(w, "Adminisztrátortól kapott kód")
        uj = mezo(w, "Új jelszó (legalább 12 karakter)", True)
        ismet = mezo(w, "Új jelszó újra", True)
        def ment():
            if uj.get() != ismet.get():
                raise ValueError("A két jelszó eltér.")
            jelszo_visszaallitas(nev.get(), kod.get().strip(), uj.get())
            w.destroy()
            messagebox.showinfo("Mentve", "Az új jelszóval bejelentkezhetsz.", parent=self)
        ctk.CTkButton(w, text="Új jelszó mentése", command=lambda: probal(w, ment)).pack(pady=20)


# A fiókkezelő felület az adminisztrátori jogosultságokat és a felhasználói fiókokat kezeli.
class FiokFelulet(ctk.CTkScrollableFrame):
    def __init__(self, master):
        super().__init__(master)
        en = aktualis()
        ctk.CTkLabel(self, text=f"Bejelentkezve: {en.Nev}").pack(pady=8)
        regi = mezo(self, "Jelenlegi jelszó", True)
        uj = mezo(self, "Új jelszó (legalább 12 karakter)", True)
        ismet = mezo(self, "Új jelszó újra", True)
        def csere():
            if uj.get() != ismet.get():
                raise ValueError("A két jelszó eltér.")
            jelszo_csere(regi.get(), uj.get())
            for e in (regi, uj, ismet):
                e.delete(0, "end")
            messagebox.showinfo("Mentve", "A jelszó megváltozott.", parent=self)
        ctk.CTkButton(self, text="Saját jelszó módosítása", command=lambda: probal(self, csere)).pack(pady=15)
        if en.Admin:
            ctk.CTkButton(self, text="Új felhasználó", command=self.uj_fiok).pack(pady=8)
            self.sorok = ctk.CTkFrame(self)
            self.sorok.pack(fill="x", pady=15)
            self.frissit()

    def frissit(self):
        for e in self.sorok.winfo_children():
            e.destroy()
        for s in lista():
            r = ctk.CTkFrame(self.sorok)
            r.pack(fill="x", pady=4)
            ctk.CTkLabel(r, text=s.Nev, width=180).pack(side="left", padx=8)
            szerep = ctk.StringVar(value="Adminisztrátor" if s.Admin else "Megtekintő" if s.Megtekinto else "Felhasználó")
            aktiv = ctk.BooleanVar(value=bool(s.Aktiv))
            ctk.CTkOptionMenu(r, values=["Adminisztrátor", "Felhasználó", "Megtekintő"], variable=szerep).pack(side="left", padx=5)
            ctk.CTkCheckBox(r, text="Aktív", variable=aktiv).pack(side="left")
            def ment(az=s.FelhasznaloID, a=szerep, b=aktiv):
                fiok_modositasa(az, a.get()=="Adminisztrátor", b.get(), megtekinto=a.get()=="Megtekintő")
                messagebox.showinfo("Mentve", "Jogosultságok mentve. A módosított fióknak újra be kell lépnie.", parent=self)
                self.frissit()
            ctk.CTkButton(r, text="Mentés", width=85, command=lambda fn=ment: probal(self, fn)).pack(side="left", padx=4)
            ctk.CTkButton(r, text="Visszaállító kód", command=lambda az=s.FelhasznaloID: probal(self, lambda: self.reset(az))).pack(side="left", padx=4)

    def reset(self, az):
        kod = reset_kiadasa(az)
        w = FelugroAblak(self)
        w.title("Egyszer használható kód")
        w.geometry("600x200")
        ctk.CTkLabel(w, text="30 percig érvényes. Add át a felhasználónak biztonságos csatornán.\n"
                     "A belépőablakban ő állítja be a saját új jelszavát.").pack(pady=15)
        e = ctk.CTkEntry(w, width=550)
        e.pack(pady=8)
        e.insert(0, kod)
        e.configure(state="readonly")

    def uj_fiok(self):
        w = FelugroAblak(self)
        w.title("Új felhasználó")
        w.geometry("480x250")
        nev = mezo(w, "Felhasználónév")
        szerep = ctk.StringVar(value="Felhasználó")
        ctk.CTkOptionMenu(w, values=["Adminisztrátor", "Felhasználó", "Megtekintő"], variable=szerep).pack(pady=8)
        def ment():
            # Véletlen kezdőjelszót adok; a saját jelszót a felhasználó választja.
            letrehozas(nev.get(), secrets.token_urlsafe(32), admin=szerep.get()=="Adminisztrátor", megtekinto=szerep.get()=="Megtekintő")
            sor = next(s for s in lista() if s.Nev.casefold() == nev.get().strip().casefold())
            w.destroy()
            self.frissit()
            self.reset(sor.FelhasznaloID)
        ctk.CTkButton(w, text="Létrehozás", command=lambda: probal(w, ment)).pack(pady=15)


from api import bekotes
bekotes(globals(), "fiokok")
