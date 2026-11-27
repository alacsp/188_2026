"""Eszközadatok lekérdezése és módosítása."""


from adatbazis import kapcsolat_letrehozasa, lekerdezes as _lekerdezes, tranzakcio


# Az eszközműveletek az eszközadatok, helyek és törzsadat-hivatkozások kezelését végzik.
def eszkozok_lekerdezese(aktiv=True):
    return _lekerdezes("""
        SELECT e.EszkozID, e.LeltariSzam,
               g.Nev AS Gyarto, m.Nev AS Modell,
               s.Nev AS Statusz,
               CASE WHEN h.HelyID IS NULL THEN NULL
                    ELSE CONCAT(
                        t.Nev, ' / ',
                        ISNULL(tr.Nev + ' / ', ''),
                        h.Nev,
                        CASE WHEN e.RackPozicioKezdet IS NOT NULL
                             THEN CONCAT(' / U', e.RackPozicioKezdet)
                             ELSE '' END
                    )
               END AS Hely
        FROM eszkoz.Eszkoz AS e
        JOIN torzs.Modell AS m ON e.ModellID = m.ModellID
        JOIN torzs.Gyarto AS g ON m.GyartoID = g.GyartoID
        JOIN torzs.Statusz AS s ON e.StatuszID = s.StatuszID
        LEFT JOIN infrastruktura.Hely AS h ON e.HelyID = h.HelyID
        LEFT JOIN infrastruktura.Telephely AS t
            ON h.TelephelyID = t.TelephelyID
        LEFT JOIN infrastruktura.Terem AS tr
            ON h.TeremID = tr.TeremID
        WHERE e.Aktiv = ?
        ORDER BY e.LeltariSzam
    """, (int(aktiv),))


def torzsadatok_lekerdezese(modell_id=None, statusz_id=None):
    """Aktív törzsadatok és szerkesztéskor a korábban kiválasztott inaktívak."""
    modellek = _lekerdezes("""
        SELECT m.ModellID, g.Nev AS Gyarto, m.Nev AS Modell,
               CASE WHEN m.Aktiv = 1 AND g.Aktiv = 1 AND et.Aktiv = 1
                    THEN 1 ELSE 0 END AS Aktiv
        FROM torzs.Modell AS m
        JOIN torzs.Gyarto AS g ON m.GyartoID = g.GyartoID
        JOIN torzs.EszkozTipus AS et ON m.EszkozTipusID = et.EszkozTipusID
        WHERE (m.Aktiv = 1 AND g.Aktiv = 1 AND et.Aktiv = 1)
           OR m.ModellID = ?
        ORDER BY g.Nev, m.Nev
    """, (modell_id,))
    statuszok = _lekerdezes("""
        SELECT StatuszID, Nev, Aktiv
        FROM torzs.Statusz
        WHERE Aktiv = 1 OR StatuszID = ?
        ORDER BY Nev
    """, (statusz_id,))
    return modellek, statuszok


def eszkoz_adatainak_lekerdezese(eszkoz_id):
    return _lekerdezes("""
        SELECT EszkozID, LeltariSzam, Sorozatszam,
            ModellID, StatuszID, Megjegyzes, HelyID, RackPozicioKezdet, UzembehelyezesDatuma
        FROM eszkoz.Eszkoz
        WHERE EszkozID = ? AND Aktiv = 1
    """, (eszkoz_id,), egy=True)


def _eszkoz_ertekek(leltari_szam, sorozatszam, megjegyzes):
    """A SQL-oszlophosszoknak megfelelő mezőellenőrzés."""
    leltari_szam = (leltari_szam or "").strip()
    sorozatszam = (sorozatszam or "").strip() or None
    megjegyzes = (megjegyzes or "").strip() or None
    if not leltari_szam or len(leltari_szam) > 50:
        raise ValueError("A leltári szám kötelező, és legfeljebb 50 karakter lehet.")
    if sorozatszam is not None and len(sorozatszam) > 100:
        raise ValueError("A sorozatszám legfeljebb 100 karakter lehet.")
    if megjegyzes is not None and len(megjegyzes) > 1000:
        raise ValueError("A megjegyzés legfeljebb 1000 karakter lehet.")
    return leltari_szam, sorozatszam, megjegyzes


def _referenciak_ellenorzese(kurzor, modell_id, statusz_id,
                             regi_modell=None, regi_statusz=None):
    # A korábban kiválasztott inaktív törzsadatot megtartom.
    kurzor.execute("""
        SELECT m.MagassagU,
               CASE WHEN m.Aktiv = 1 AND g.Aktiv = 1 AND et.Aktiv = 1
                    THEN 1 ELSE 0 END AS Aktiv
        FROM torzs.Modell m
        JOIN torzs.Gyarto g ON m.GyartoID = g.GyartoID
        JOIN torzs.EszkozTipus et ON m.EszkozTipusID = et.EszkozTipusID
        WHERE m.ModellID = ?
    """, (modell_id,))
    modell = kurzor.fetchone()
    if modell is None or (not modell.Aktiv and modell_id != regi_modell):
        raise ValueError("A kiválasztott modell nem aktív vagy nem található.")
    kurzor.execute("""
        SELECT Kod, Aktiv FROM torzs.Statusz WHERE StatuszID = ?
    """, (statusz_id,))
    statusz = kurzor.fetchone()
    if statusz is None or (not statusz.Aktiv and statusz_id != regi_statusz):
        raise ValueError("A kiválasztott státusz nem aktív vagy nem található.")
    return modell.MagassagU, statusz.Kod


def eszkoz_rogzitese(leltari_szam, sorozatszam, modell_id, statusz_id, megjegyzes, uzembehelyezes="auto"):
    from ellenorzes import datum
    nap = datum(uzembehelyezes, "üzembe helyezés") if uzembehelyezes != "auto" else None
    leltari_szam, sorozatszam, megjegyzes = _eszkoz_ertekek(
        leltari_szam, sorozatszam, megjegyzes)

    def mentes(k):
        _, statusz_kod = _referenciak_ellenorzese(k, modell_id, statusz_id)
        k.execute("""
            INSERT INTO eszkoz.Eszkoz
                (LeltariSzam, Sorozatszam, ModellID, StatuszID,
                 Megjegyzes, UzembehelyezesDatuma)
            VALUES (?, ?, ?, ?, ?, CASE WHEN ? = N'UZEMBEN'
                                      THEN CAST(GETDATE() AS DATE) ELSE NULL END);
            SELECT CAST(SCOPE_IDENTITY() AS INT);
        """, (leltari_szam, sorozatszam, modell_id,
              statusz_id, megjegyzes, statusz_kod))
        while k.description is None:
            k.nextset()
        uj_id = k.fetchone()[0]
        if uzembehelyezes != "auto":
            k.execute("UPDATE eszkoz.Eszkoz SET UzembehelyezesDatuma=? WHERE EszkozID=?", (nap, uj_id))

    tranzakcio(mentes)


def eszkoz_modositasa(eszkoz_id, leltari_szam, sorozatszam,
                     modell_id, statusz_id, megjegyzes, uzembehelyezes="auto"):
    from ellenorzes import datum
    nap = datum(uzembehelyezes, "üzembe helyezés") if uzembehelyezes != "auto" else None
    leltari_szam, sorozatszam, megjegyzes = _eszkoz_ertekek(
        leltari_szam, sorozatszam, megjegyzes)

    def mentes(k):
        k.execute("""
            SELECT ModellID, StatuszID, HelyID, RackPozicioKezdet
            FROM eszkoz.Eszkoz WITH (UPDLOCK, HOLDLOCK)
            WHERE EszkozID = ? AND Aktiv = 1
        """, (eszkoz_id,))
        regi = k.fetchone()
        if regi is None:
            raise ValueError("A kiválasztott aktív eszköz nem található.")

        magassag, statusz_kod = _referenciak_ellenorzese(
            k, modell_id, statusz_id, regi.ModellID, regi.StatuszID)

        # Ellenőrzöm, hogy az új magasság elfér-e a rackben, ütközés nélkül.
        if regi.RackPozicioKezdet is not None:
            k.execute("""
                SELECT r.MagassagU
                FROM infrastruktura.Hely h WITH (UPDLOCK, HOLDLOCK)
                JOIN infrastruktura.Rack r ON r.HelyID = h.HelyID
                WHERE h.HelyID = ?
            """, (regi.HelyID,))
            rack = k.fetchone()
            if rack is None or magassag is None:
                raise ValueError("A rack vagy az új modell U-magassága hiányzik.")
            if regi.RackPozicioKezdet + magassag - 1 > rack.MagassagU:
                raise ValueError("Az új modell kilógna a rackből.")
            k.execute("""
                SELECT e.RackPozicioKezdet, m.MagassagU
                FROM eszkoz.Eszkoz e
                JOIN torzs.Modell m ON e.ModellID = m.ModellID
                WHERE e.HelyID = ? AND e.EszkozID <> ? AND e.Aktiv = 1
                  AND e.RackPozicioKezdet IS NOT NULL
            """, (regi.HelyID, eszkoz_id))
            for masik in k.fetchall():
                if masik.MagassagU is None or (
                    regi.RackPozicioKezdet <= masik.RackPozicioKezdet + masik.MagassagU - 1
                    and masik.RackPozicioKezdet <= regi.RackPozicioKezdet + magassag - 1
                ):
                    raise ValueError("Az új modell átfedne egy másik rackes eszközt.")

        k.execute("""
            UPDATE eszkoz.Eszkoz
            SET LeltariSzam = ?, Sorozatszam = ?, ModellID = ?,
                StatuszID = ?, Megjegyzes = ?,
                UzembehelyezesDatuma = CASE
                    WHEN UzembehelyezesDatuma IS NULL AND ? = N'UZEMBEN'
                    THEN CAST(GETDATE() AS DATE)
                    ELSE UzembehelyezesDatuma END
            WHERE EszkozID = ? AND Aktiv = 1
        """, (leltari_szam, sorozatszam, modell_id,
              statusz_id, megjegyzes, statusz_kod, eszkoz_id))
        if k.rowcount != 1:
            raise ValueError("Az eszköz módosítása nem sikerült.")
        if uzembehelyezes != "auto":
            k.execute("UPDATE eszkoz.Eszkoz SET UzembehelyezesDatuma=? WHERE EszkozID=?", (nap, eszkoz_id))

    tranzakcio(mentes)


def eszkoz_inaktivalasa(eszkoz_id):
    """A hálózati adatok előzetes rendezését kötelezővé teszi."""
    def mentes(k):
        k.execute("""
            SELECT Aktiv FROM eszkoz.Eszkoz WITH (UPDLOCK, HOLDLOCK)
            WHERE EszkozID = ?
        """, (eszkoz_id,))
        rekord = k.fetchone()
        if rekord is None or not rekord.Aktiv:
            raise ValueError("Az aktív eszköz nem található.")
        k.execute("""
            SELECT COUNT(*)
            FROM halozat.HalozatiInterfesz
            WHERE EszkozID = ? AND Aktiv = 1
        """, (eszkoz_id,))
        if k.fetchone()[0]:
            raise ValueError(
                "Előbb inaktiváld az eszköz aktív hálózati interfészeit és IP-címeit.")
        k.execute("""
            SELECT COUNT(*)
            FROM halozat.IPCim i
            JOIN halozat.HalozatiInterfesz h
                ON h.HalozatiInterfeszID = i.HalozatiInterfeszID
            WHERE h.EszkozID = ? AND i.Aktiv = 1
        """, (eszkoz_id,))
        if k.fetchone()[0]:
            raise ValueError("Előbb inaktiváld az eszköz aktív IP-címeit.")
        k.execute("""
            UPDATE eszkoz.Eszkoz SET Aktiv = 0
            WHERE EszkozID = ? AND Aktiv = 1
        """, (eszkoz_id,))
        if k.rowcount != 1:
            raise ValueError("Az eszköz inaktiválása nem sikerült.")

    tranzakcio(mentes)


def eszkoz_visszaallitasa(eszkoz_id):
    kapcsolat = kapcsolat_letrehozasa()
    try:
        kurzor = kapcsolat.cursor()
        from fiokok import jogosult
        jogosult(kurzor, iras=True)
        kurzor.execute("""
            SELECT HelyID, RackPozicioKezdet
            FROM eszkoz.Eszkoz WITH (UPDLOCK)
            WHERE EszkozID = ? AND Aktiv = 0
        """, (eszkoz_id,))

        adat = kurzor.fetchone()
        if adat is None:
            raise ValueError("Az inaktív eszköz nem található.")

        uj_hely = adat.HelyID
        if adat.HelyID is not None:
            kurzor.execute("""
                SELECT 1 FROM infrastruktura.Hely h
                JOIN infrastruktura.Telephely t ON t.TelephelyID = h.TelephelyID
                LEFT JOIN infrastruktura.Terem r ON r.TeremID = h.TeremID
                WHERE h.HelyID = ? AND h.Aktiv = 1 AND t.Aktiv = 1
                  AND (r.TeremID IS NULL OR r.Aktiv = 1)
            """, (adat.HelyID,))
            if kurzor.fetchone() is None:
                uj_hely = None

        kurzor.execute("""
            UPDATE eszkoz.Eszkoz
            SET Aktiv = 1, HelyID = ?, RackPozicioKezdet = NULL
            WHERE EszkozID = ? AND Aktiv = 0
        """, (uj_hely, eszkoz_id))
        if kurzor.rowcount != 1:
            raise ValueError("Az eszköz visszaállítása nem sikerült.")

        if adat.HelyID != uj_hely or adat.RackPozicioKezdet is not None:
            kurzor.execute("""
                INSERT INTO eszkoz.EszkozMozgas
                    (EszkozID, RegiHelyID, UjHelyID, RegiRackPozicio)
                VALUES (?, ?, ?, ?)
            """, (eszkoz_id, adat.HelyID, uj_hely, adat.RackPozicioKezdet))

        kapcsolat.commit()
    except Exception:
        kapcsolat.rollback()
        raise
    finally:
        kapcsolat.close()


def helyek_lekerdezese():
    return _lekerdezes("""
        SELECT h.HelyID, t.Nev AS Telephely,
               tr.Nev AS Terem, h.Nev AS Hely,
               ht.Kod AS HelyTipus,
               r.MagassagU AS RackMagassag
        FROM infrastruktura.Hely AS h
        JOIN infrastruktura.Telephely AS t
            ON h.TelephelyID = t.TelephelyID
        LEFT JOIN infrastruktura.Terem AS tr
            ON h.TeremID = tr.TeremID
        JOIN torzs.HelyTipus AS ht
            ON h.HelyTipusID = ht.HelyTipusID
        LEFT JOIN infrastruktura.Rack AS r
            ON h.HelyID = r.HelyID
        WHERE h.Aktiv = 1 AND t.Aktiv = 1
          AND (tr.TeremID IS NULL OR tr.Aktiv = 1)
        ORDER BY t.Nev, tr.Nev, h.Nev
    """)

def eszkoz_helyenek_modositasa(eszkoz_id, hely_id, pozicio):
    kapcsolat = kapcsolat_letrehozasa()
    try:
        kurzor = kapcsolat.cursor()
        from fiokok import jogosult
        jogosult(kurzor, iras=True)

        kurzor.execute("""
            SELECT e.HelyID, e.RackPozicioKezdet, m.MagassagU
            FROM eszkoz.Eszkoz AS e WITH (UPDLOCK)
            JOIN torzs.Modell AS m ON e.ModellID = m.ModellID
            WHERE e.EszkozID = ? AND e.Aktiv = 1
        """, (eszkoz_id,))

        regi = kurzor.fetchone()
        if regi is None:
            raise ValueError("Az aktív eszköz nem található.")

        if hely_id is None:
            if pozicio is not None:
                raise ValueError("Hely nélkül rackpozíció sem adható meg.")
        else:
            kurzor.execute("""
                SELECT ht.Kod, r.MagassagU
                FROM infrastruktura.Hely AS h WITH (UPDLOCK, HOLDLOCK)
                JOIN infrastruktura.Telephely AS t
                    ON h.TelephelyID = t.TelephelyID
                LEFT JOIN infrastruktura.Terem AS tr
                    ON h.TeremID = tr.TeremID
                JOIN torzs.HelyTipus AS ht
                    ON h.HelyTipusID = ht.HelyTipusID
                LEFT JOIN infrastruktura.Rack AS r
                    ON h.HelyID = r.HelyID
                WHERE h.HelyID = ? AND h.Aktiv = 1 AND t.Aktiv = 1
                  AND (tr.TeremID IS NULL OR tr.Aktiv = 1)
            """, (hely_id,))

            hely = kurzor.fetchone()
            if hely is None:
                raise ValueError("A kiválasztott hely nem található vagy inaktív.")

            if hely.Kod == "RACK":
                if hely.MagassagU is None:
                    raise ValueError("A rack magassága nincs megadva.")

                if pozicio is None or regi.MagassagU is None:
                    raise ValueError(
                        "A rackpozíció és az eszköz U-magassága kötelező."
                    )

                if not 1 <= pozicio <= hely.MagassagU - regi.MagassagU + 1:
                    raise ValueError(
                        "Az eszköz nem fér el a rack ezen pozícióján."
                    )

                kurzor.execute("""
                    SELECT e.RackPozicioKezdet, m.MagassagU
                    FROM eszkoz.Eszkoz AS e
                    JOIN torzs.Modell AS m ON e.ModellID = m.ModellID
                    WHERE e.HelyID = ? AND e.Aktiv = 1
                      AND e.EszkozID <> ?
                      AND e.RackPozicioKezdet IS NOT NULL
                """, (hely_id, eszkoz_id))

                for masik in kurzor.fetchall():
                    if masik.MagassagU is None:
                        raise ValueError(
                            "Másik eszköz U-magassága hiányzik a rackben."
                        )

                    if (
                        pozicio <= masik.RackPozicioKezdet + masik.MagassagU - 1
                        and masik.RackPozicioKezdet <= pozicio + regi.MagassagU - 1
                    ):
                        raise ValueError("Ez a rackpozíció már foglalt.")

            elif pozicio is not None:
                raise ValueError(
                    "Csak rack típusú helyhez adható meg U-pozíció."
                )

        if regi.HelyID != hely_id or regi.RackPozicioKezdet != pozicio:
            kurzor.execute("""
                UPDATE eszkoz.Eszkoz
                SET HelyID = ?, RackPozicioKezdet = ?
                WHERE EszkozID = ? AND Aktiv = 1
            """, (hely_id, pozicio, eszkoz_id))

            kurzor.execute("""
                INSERT INTO eszkoz.EszkozMozgas
                    (EszkozID, RegiHelyID, UjHelyID,
                     RegiRackPozicio, UjRackPozicio)
                VALUES (?, ?, ?, ?, ?)
            """, (
                eszkoz_id, regi.HelyID, hely_id,
                regi.RackPozicioKezdet, pozicio
            ))

        kapcsolat.commit()

    except Exception:
        kapcsolat.rollback()
        raise
    finally:
        kapcsolat.close()


if __name__ == "__main__":
    try:
        eszkozok = eszkozok_lekerdezese()
        print(f"Talált aktív eszközök: {len(eszkozok)}")
        for eszkoz in eszkozok:
            print(eszkoz.LeltariSzam, eszkoz.Gyarto, eszkoz.Modell,
                  eszkoz.Statusz, eszkoz.Hely or "Nincs megadva", sep=" | ")
    except Exception as hiba:
        print(f"Hiba: {hiba}")



# A főoldali összesítések a nyilvántartás fő darabszámait adják vissza.
def fooldal_statisztika():
    """Lekérdezem a főoldal összesítéseit."""
    return _lekerdezes("""
                    SELECT
                        (SELECT COUNT(*)
                         FROM eszkoz.Eszkoz
                         WHERE Aktiv = 1) AS AktivEszkoz,

                        (SELECT COUNT(*)
                         FROM eszkoz.Eszkoz e
                         JOIN torzs.Statusz s
                            ON e.StatuszID = s.StatuszID
                         WHERE e.Aktiv = 1
                           AND s.Kod = N'UZEMBEN') AS Uzemben,

                        (SELECT COUNT(*)
                         FROM eszkoz.Eszkoz e
                         JOIN torzs.Statusz s
                            ON e.StatuszID = s.StatuszID
                         WHERE e.Aktiv = 1
                           AND s.Kod = N'HIBAS') AS Hibas,

                        (SELECT COUNT(*)
                         FROM eszkoz.Eszkoz e
                         JOIN torzs.Statusz s
                            ON e.StatuszID = s.StatuszID
                         WHERE e.Aktiv = 1
                           AND s.Kod = N'KARBANTARTAS') AS Karbantartas,

                        (SELECT COUNT(*)
                         FROM infrastruktura.Telephely
                         WHERE Aktiv = 1) AS Telephely,

                        (SELECT COUNT(*)
                         FROM eszkoz.Garancia g
                         JOIN eszkoz.Eszkoz e
                            ON g.EszkozID = e.EszkozID
                         WHERE g.Aktiv = 1
                           AND e.Aktiv = 1
                           AND g.GaranciaVege BETWEEN
                               CAST(GETDATE() AS DATE)
                               AND DATEADD(
                                   DAY, 30, CAST(GETDATE() AS DATE)
                               )) AS LejaroGarancia
                """, egy=True)


from api import bekotes
bekotes(globals(), "eszkozok")
