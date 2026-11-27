USE EszkozNyilvantartas;
GO

--------------------
-- GYÁRTÓ ADATOK  --
--------------------

INSERT INTO torzs.Gyarto (Nev)
SELECT v.Nev
FROM (VALUES
    (N'Dell'),
    (N'HPE'),
    (N'Cisco'),
    (N'Fortinet'),
    (N'Juniper'),
    (N'MikroTik'),
    (N'APC'),
    (N'Eaton'),
    (N'Vertiv'),
    (N'Synology')
) v(Nev)
WHERE NOT EXISTS
(
    SELECT 1
    FROM torzs.Gyarto g
    WHERE g.Nev = v.Nev
);
GO

--------------------------
-- ESZKÖZ TÍPUS ADATOK  --
--------------------------

INSERT INTO torzs.EszkozTipus (Nev, Leiras)
SELECT v.Nev, v.Leiras
FROM (VALUES
    (N'Szerver',       N'Fizikai kiszolgáló eszköz'),
    (N'Switch',        N'Hálózati kapcsoló'),
    (N'Router',        N'Hálózati útválasztó'),
    (N'Tűzfal',        N'Hálózatbiztonsági eszköz'),
    (N'Tároló',        N'Adattároló rendszer'),
    (N'UPS',           N'Szünetmentes tápegység'),
    (N'PDU',           N'Rack szintű áramelosztó egység'),
    (N'KVM',           N'Konzol- és KVM eszköz'),
    (N'Konzolszerver', N'Távoli konzolelérést biztosító eszköz'),
    (N'Egyéb',         N'Egyéb informatikai eszköz')
) v(Nev, Leiras)
WHERE NOT EXISTS
(
    SELECT 1
    FROM torzs.EszkozTipus et
    WHERE et.Nev = v.Nev
);
GO

---------------------
-- STÁTUSZ ADATOK  --
---------------------

INSERT INTO torzs.Statusz (Kod, Nev, Leiras)
SELECT v.Kod, v.Nev, v.Leiras
FROM (VALUES
    (N'RAKTARON',      N'Raktáron',             N'Az eszköz raktárban található, még nincs üzembe helyezve'),
    (N'TELEPITES',     N'Telepítés alatt',      N'Az eszköz telepítése vagy üzembe helyezése folyamatban van'),
    (N'UZEMBEN',       N'Üzemben',              N'Az eszköz normál üzemben működik'),
    (N'TARTALEK',      N'Tartalék',              N'Működőképes, tartalékként fenntartott eszköz'),
    (N'KARBANTARTAS',  N'Karbantartás alatt',   N'Az eszköz karbantartása vagy javítása folyamatban van'),
    (N'HIBAS',         N'Hibás',                 N'Az eszköz meghibásodott és nem használható normál üzemben'),
    (N'KIVEZETES',     N'Kivezetés alatt',       N'Az eszköz kivonása folyamatban van'),
    (N'SELEJTEZETT',   N'Selejtezett',           N'Az eszköz életciklusa lezárult')
) v(Kod, Nev, Leiras)
WHERE NOT EXISTS
(
    SELECT 1
    FROM torzs.Statusz s
    WHERE s.Kod = v.Kod
);
GO

-------------------------
-- HELY TÍPUS ADATOK --
-------------------------

INSERT INTO torzs.HelyTipus (Kod, Nev, Leiras)
SELECT v.Kod, v.Nev, v.Leiras
FROM (VALUES
    (N'RACK',    N'Rack szekrény', N'Rack szekrényben kialakított eszközhely'),
    (N'POLC',    N'Raktári polc',  N'Raktári vagy tárolási hely'),
    (N'SZERVIZ', N'Szervizhely',   N'Karbantartásra vagy javításra kijelölt hely'),
    (N'PADLO',   N'Padlóhely',     N'Rackbe nem szerelt berendezés helye'),
    (N'EGYEB',   N'Egyéb hely',    N'Egyéb eszközelhelyezési hely')
) v(Kod, Nev, Leiras)
WHERE NOT EXISTS
(
    SELECT 1
    FROM torzs.HelyTipus ht
    WHERE ht.Kod = v.Kod
);
GO

--------------------
-- MODELL ADATOK --
--------------------

INSERT INTO torzs.Modell
(
    GyartoID,
    EszkozTipusID,
    Nev,
    MagassagU
)
SELECT
    g.GyartoID,
    et.EszkozTipusID,
    v.ModellNev,
    v.MagassagU
FROM (VALUES
    (N'Dell',     N'Szerver', N'PowerEdge R640',          CAST(1 AS TINYINT)),
    (N'Dell',     N'Szerver', N'PowerEdge R740',          CAST(2 AS TINYINT)),
    (N'HPE',      N'Szerver', N'ProLiant DL360 Gen10',    CAST(1 AS TINYINT)),
    (N'HPE',      N'Szerver', N'ProLiant DL380 Gen10',    CAST(2 AS TINYINT)),
    (N'Cisco',    N'Switch',  N'Catalyst 9200L',          CAST(1 AS TINYINT)),
    (N'Cisco',    N'Switch',  N'Nexus 93180YC-FX',        CAST(1 AS TINYINT)),
    (N'Fortinet', N'Tűzfal',  N'FortiGate 100F',          CAST(1 AS TINYINT)),
    (N'Synology', N'Tároló',  N'RS3621xs+',               CAST(2 AS TINYINT)),
    (N'APC',      N'UPS',     N'Smart-UPS SRT 3000VA RM', CAST(2 AS TINYINT))
) v(GyartoNev, EszkozTipusNev, ModellNev, MagassagU)

INNER JOIN torzs.Gyarto g
    ON g.Nev = v.GyartoNev

INNER JOIN torzs.EszkozTipus et
    ON et.Nev = v.EszkozTipusNev

WHERE NOT EXISTS
(
    SELECT 1
    FROM torzs.Modell m
    WHERE m.GyartoID = g.GyartoID
      AND m.Nev = v.ModellNev
);
GO

---------------------------
-- KARBANTARTÁS TÍPUS ADATOK --
---------------------------

INSERT INTO torzs.KarbantartasTipus (Kod, Nev)
SELECT v.Kod, v.Nev
FROM (VALUES
    (N'TERVEZETT', N'Tervezett karbantartás'),
    (N'HIBAELHARITAS', N'Hibaelhárítás'),
    (N'ALKATRESZ_CSERE', N'Alkatrészcsere'),
    (N'FIRMWARE', N'Firmware-frissítés'),
    (N'TISZTITAS', N'Tisztítás'),
    (N'EGYEB', N'Egyéb')
) v(Kod, Nev)
WHERE NOT EXISTS (
    SELECT 1
    FROM torzs.KarbantartasTipus t
    WHERE t.Kod = v.Kod
);
GO

---------------------------
-- GARANCIA TÍPUS ADATOK --
---------------------------

INSERT INTO torzs.GaranciaTipus (Kod, Nev)
SELECT v.Kod, v.Nev
FROM (VALUES
    (N'GYARTOI', N'Gyártói garancia'),
    (N'KITERJESZTETT', N'Kiterjesztett garancia'),
    (N'SZERVIZ', N'Szervizszerződés'),
    (N'EGYEB', N'Egyéb')
) v(Kod, Nev)
WHERE NOT EXISTS (
    SELECT 1 FROM torzs.GaranciaTipus t WHERE t.Kod = v.Kod
);
GO

---------------------
--Kapcsolat-típusok--
---------------------

INSERT INTO torzs.KapcsolatTipus (Kod, Nev)
SELECT v.Kod, v.Nev
FROM (VALUES
    (N'TULAJDONOS', N'Tulajdonos'),
    (N'BERLO', N'Bérlő'),
    (N'HASZNALO', N'Használó'),
    (N'UZEMELTETO', N'Üzemeltető')
) v(Kod, Nev)
WHERE NOT EXISTS (
    SELECT 1 FROM torzs.KapcsolatTipus t WHERE t.Kod = v.Kod
);
GO