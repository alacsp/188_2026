"""Dátumok és pénzösszegek ellenőrzése."""


from datetime import date
from decimal import Decimal, InvalidOperation, localcontext


# A mezőellenőrzők egységes formátumra alakítják és ellenőrzik az űrlapértékeket.
def datum(ertek, nev, kotelezo=False):
    szoveg = str(ertek if ertek is not None else "").strip()
    if not szoveg and not kotelezo:
        return None
    try:
        eredmeny = date.fromisoformat(szoveg)
        if eredmeny.isoformat() != szoveg:
            raise ValueError
        return eredmeny
    except ValueError as hiba:
        raise ValueError(f"A(z) {nev} ÉÉÉÉ-HH-NN formátumú legyen.") from hiba


def penzosszeg(ertek, nev):
    szoveg = str(ertek if ertek is not None else "").strip()
    szoveg = szoveg.replace(" ", "").replace("\u00a0", "").replace(",", ".")
    if not szoveg:
        return None
    try:
        osszeg = Decimal(szoveg)
        if not osszeg.is_finite() or not 0 <= osszeg < Decimal("10000000000000000"):
            raise ValueError
        with localcontext() as kontextus:
            kontextus.prec = 28
            kerekitett = osszeg.quantize(Decimal("0.01"))
        if osszeg != kerekitett:
            raise ValueError
        return kerekitett
    except (ValueError, InvalidOperation) as hiba:
        raise ValueError(
            f"A(z) {nev} nemnegatív, 10^16-nál kisebb, "
            "legfeljebb két tizedesjegyű szám legyen."
        ) from hiba


def szoveg(ertek, maximum, nev):
    """Ellenőrzöm a szöveg hosszát, az üres értéket hiányzó adatként kezelem."""
    eredmeny = (ertek or "").strip()
    if len(eredmeny) > maximum:
        raise ValueError(f"A(z) {nev} legfeljebb {maximum} karakter lehet.")
    return eredmeny or None
