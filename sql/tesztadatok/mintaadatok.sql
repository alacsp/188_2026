USE EszkozNyilvantartas;
GO



SET XACT_ABORT ON;

IF OBJECT_ID(N'torzs.Modell', N'U') IS NULL
   OR OBJECT_ID(N'torzs.Statusz', N'U') IS NULL
   OR OBJECT_ID(N'infrastruktura.Telephely', N'U') IS NULL
   OR OBJECT_ID(N'eszkoz.Eszkoz', N'U') IS NULL
    THROW 51010, N'Előbb telepítsd az adatbázist.', 1;
GO

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM torzs.HelyTipus WHERE Kod = N'RACK')
       OR NOT EXISTS (SELECT 1 FROM torzs.Statusz WHERE Kod = N'UZEMBEN')
       OR NOT EXISTS (SELECT 1 FROM torzs.Statusz WHERE Kod = N'TARTALEK')
       OR NOT EXISTS (SELECT 1 FROM torzs.GaranciaTipus WHERE Kod = N'GYARTOI')
       OR NOT EXISTS (SELECT 1 FROM torzs.GaranciaTipus WHERE Kod = N'KITERJESZTETT')
       OR NOT EXISTS (SELECT 1 FROM torzs.KarbantartasTipus WHERE Kod = N'TERVEZETT')
       OR NOT EXISTS (SELECT 1 FROM torzs.KarbantartasTipus WHERE Kod = N'FIRMWARE')
       OR NOT EXISTS (SELECT 1 FROM torzs.KarbantartasTipus WHERE Kod = N'TISZTITAS')
       OR NOT EXISTS (SELECT 1 FROM torzs.KarbantartasTipus WHERE Kod = N'ALKATRESZ_CSERE')
        THROW 51011, N'Hiányoznak a szükséges törzsadatok. Futtasd előbb a 09_torzsadatok.sql fájlt.', 1;
    IF EXISTS (
        SELECT 1
        FROM eszkoz.Eszkoz
        WHERE LeltariSzam NOT LIKE N'MINTA-[0-9][0-9][0-9]'
    )
        THROW 51012, N'A tesztadatok csak üres vagy már ezzel a MINTA- azonosítóval részben feltöltött adatbázisba tölthetők. Más eszközrekordot a script nem módosít.', 1;

    DECLARE @TelephelyNev NVARCHAR(150) = N'Budapesti minta-adatközpont';
    DECLARE @TelephelyID INT;

    IF NOT EXISTS (SELECT 1 FROM infrastruktura.Telephely WHERE Nev = @TelephelyNev)
        INSERT INTO infrastruktura.Telephely (Nev, Varos, Cim)
        VALUES (@TelephelyNev, N'Budapest', N'Minta utca 1.');

    SELECT @TelephelyID = TelephelyID
    FROM infrastruktura.Telephely
    WHERE Nev = @TelephelyNev;

    INSERT INTO infrastruktura.Terem (TelephelyID, Nev, Leiras)
    SELECT @TelephelyID, v.Nev, v.Leiras
    FROM (VALUES
        (N'1. gépterem', N'Fő szerverterem, A jelű rack.'),
        (N'2. gépterem', N'Kiegészítő szerverterem, B jelű rack.')
    ) v(Nev, Leiras)
    WHERE NOT EXISTS (
        SELECT 1
        FROM infrastruktura.Terem t
        WHERE t.TelephelyID = @TelephelyID
          AND t.Nev = v.Nev
    );

    INSERT INTO infrastruktura.Hely (TelephelyID, TeremID, HelyTipusID, Nev, Leiras)
    SELECT @TelephelyID, t.TeremID, ht.HelyTipusID, v.HelyNev, v.Leiras
    FROM (VALUES
        (N'1. gépterem', N'A01 rack', N'42U magas szabványos rack, az első gépteremben.'),
        (N'1. gépterem', N'A02 rack', N'42U magas szabványos rack, az első gépteremben.'),
        (N'2. gépterem', N'B01 rack', N'42U magas szabványos rack, a második gépteremben.'),
        (N'2. gépterem', N'B02 rack', N'42U magas szabványos rack, a második gépteremben.')
    ) v(TeremNev, HelyNev, Leiras)
    INNER JOIN infrastruktura.Terem t
        ON t.TelephelyID = @TelephelyID
       AND t.Nev = v.TeremNev
    INNER JOIN torzs.HelyTipus ht
        ON ht.Kod = N'RACK'
    WHERE NOT EXISTS (
        SELECT 1
        FROM infrastruktura.Hely h
        WHERE h.TelephelyID = @TelephelyID
          AND h.Nev = v.HelyNev
    );

    INSERT INTO infrastruktura.Rack (HelyID, MagassagU)
    SELECT h.HelyID, 42
    FROM infrastruktura.Hely h
    WHERE h.TelephelyID = @TelephelyID
      AND h.Nev IN (N'A01 rack', N'A02 rack', N'B01 rack', N'B02 rack')
      AND NOT EXISTS (
          SELECT 1
          FROM infrastruktura.Rack r
          WHERE r.HelyID = h.HelyID
      );

    DECLARE @Minta TABLE (
        LeltariSzam NVARCHAR(50) NOT NULL PRIMARY KEY,
        Sorozatszam NVARCHAR(100) NOT NULL,
        GyartoNev NVARCHAR(100) NOT NULL,
        ModellNev NVARCHAR(150) NOT NULL,
        StatuszKod NVARCHAR(30) NOT NULL,
        RackNev NVARCHAR(150) NOT NULL,
        RackPozicioKezdet TINYINT NOT NULL,
        UzembehelyezesDatuma DATE NOT NULL,
        BeszallitoNev NVARCHAR(200) NOT NULL,
        BeszerzesDatuma DATE NOT NULL,
        BeszerzesiAr DECIMAL(18,2) NOT NULL,
        GaranciaKod NVARCHAR(30) NOT NULL,
        GaranciaKezdete DATE NOT NULL,
        GaranciaVege DATE NOT NULL,
        KarbantartasKod NVARCHAR(30) NOT NULL,
        BejelentesDatuma DATETIME2 NOT NULL,
        KezdesDatuma DATETIME2 NOT NULL,
        BefejezesDatuma DATETIME2 NOT NULL,
        KarbantartasLeiras NVARCHAR(1000) NOT NULL,
        KarbantartasEredmeny NVARCHAR(1000) NOT NULL,
        MACCim CHAR(17) NOT NULL,
        IPCim NVARCHAR(45) NOT NULL
    );

    INSERT INTO @Minta VALUES
    (N'MINTA-001', N'SN-MINTA-001', N'Dell', N'PowerEdge R640', N'UZEMBEN', N'A01 rack', 1,
     '2025-01-15', N'Dell Technologies', '2025-01-10', 2450000, N'GYARTOI', '2025-01-15', '2028-01-14',
     N'TERVEZETT', '2026-01-12T08:00:00', '2026-01-12T09:00:00', '2026-01-12T10:00:00',
     N'Éves állapotfelmérés és portalanítás.', N'A vizsgálat rendben lezárult.', N'02:00:00:01:00:01', N'192.0.2.101'),
    (N'MINTA-002', N'SN-MINTA-002', N'HPE', N'ProLiant DL380 Gen10', N'UZEMBEN', N'A01 rack', 3,
     '2025-02-10', N'Hewlett Packard Enterprise', '2025-02-05', 2890000, N'KITERJESZTETT', '2025-02-10', '2029-02-09',
     N'TERVEZETT', '2026-02-10T08:00:00', '2026-02-10T09:00:00', '2026-02-10T10:00:00',
     N'Éves állapotfelmérés és firmware-ellenőrzés.', N'A firmware naprakész, hibát nem találtunk.', N'02:00:00:01:00:02', N'192.0.2.102'),
    (N'MINTA-003', N'SN-MINTA-003', N'Dell', N'PowerEdge R740', N'UZEMBEN', N'A01 rack', 5,
     '2025-03-03', N'Dell Technologies', '2025-02-27', 2550000, N'GYARTOI', '2025-03-03', '2028-03-02',
     N'FIRMWARE', '2026-03-03T08:00:00', '2026-03-03T09:00:00', '2026-03-03T09:30:00',
     N'Ütemezett firmware-ellenőrzés.', N'A verzió ellenőrizve; frissítés nem volt szükséges.', N'02:00:00:01:00:03', N'192.0.2.103'),
    (N'MINTA-004', N'SN-MINTA-004', N'Dell', N'PowerEdge R640', N'UZEMBEN', N'A02 rack', 1,
     '2025-04-14', N'Dell Technologies', '2025-04-08', 2450000, N'KITERJESZTETT', '2025-04-14', '2029-04-13',
     N'FIRMWARE', '2026-04-14T08:00:00', '2026-04-14T09:00:00', '2026-04-14T09:30:00',
     N'Ütemezett firmware-ellenőrzés.', N'A verzió ellenőrizve; frissítés nem volt szükséges.', N'02:00:00:01:00:04', N'192.0.2.104'),
    (N'MINTA-005', N'SN-MINTA-005', N'HPE', N'ProLiant DL360 Gen10', N'UZEMBEN', N'A02 rack', 3,
     '2025-05-05', N'Hewlett Packard Enterprise', '2025-04-29', 2100000, N'GYARTOI', '2025-05-05', '2028-05-04',
     N'TISZTITAS', '2026-05-05T08:00:00', '2026-05-05T09:00:00', '2026-05-05T10:00:00',
     N'Éves portalanítás és állapotellenőrzés.', N'A vizsgálat rendben lezárult.', N'02:00:00:01:00:05', N'192.0.2.105'),
    (N'MINTA-006', N'SN-MINTA-006', N'APC', N'Smart-UPS SRT 3000VA RM', N'TARTALEK', N'B02 rack', 7,
     '2025-06-16', N'Schneider Electric (APC)', '2025-06-10', 1320000, N'GYARTOI', '2025-06-16', '2028-06-15',
     N'ALKATRESZ_CSERE', '2026-06-16T08:00:00', '2026-06-16T09:00:00', '2026-06-16T10:00:00',
     N'Az akkumulátor állapotának ellenőrzése.', N'A karbantartási rekord.', N'02:00:00:01:00:06', N'192.0.2.106'),
    (N'MINTA-007', N'SN-MINTA-007', N'Dell', N'PowerEdge R740', N'UZEMBEN', N'A02 rack', 5,
     '2025-07-01', N'Dell Technologies', '2025-06-25', 2550000, N'GYARTOI', '2025-07-01', '2028-06-30',
     N'TERVEZETT', '2026-07-01T08:00:00', '2026-07-01T09:00:00', '2026-07-01T10:00:00',
     N'Éves állapotfelmérés.', N'A vizsgálat rendben lezárult.', N'02:00:00:01:00:07', N'192.0.2.107'),
    (N'MINTA-008', N'SN-MINTA-008', N'HPE', N'ProLiant DL380 Gen10', N'UZEMBEN', N'B01 rack', 1,
     '2025-08-12', N'Hewlett Packard Enterprise', '2025-08-05', 2890000, N'KITERJESZTETT', '2025-08-12', '2029-08-11',
     N'FIRMWARE', '2026-08-12T08:00:00', '2026-08-12T09:00:00', '2026-08-12T09:30:00',
     N'Firmware-ellenőrzés.', N'A firmware naprakész.', N'02:00:00:01:00:08', N'192.0.2.108'),
    (N'MINTA-009', N'SN-MINTA-009', N'Dell', N'PowerEdge R640', N'UZEMBEN', N'B01 rack', 3,
     '2025-09-03', N'Dell Technologies', '2025-08-28', 2450000, N'GYARTOI', '2025-09-03', '2028-09-02',
     N'TERVEZETT', '2026-09-03T08:00:00', '2026-09-03T09:00:00', '2026-09-03T10:00:00',
     N'Éves állapotfelmérés.', N'A vizsgálat rendben lezárult.', N'02:00:00:01:00:09', N'192.0.2.109'),
    (N'MINTA-010', N'SN-MINTA-010', N'HPE', N'ProLiant DL360 Gen10', N'UZEMBEN', N'B01 rack', 5,
     '2025-10-14', N'Hewlett Packard Enterprise', '2025-10-08', 2100000, N'GYARTOI', '2025-10-14', '2028-10-13',
     N'TISZTITAS', '2026-10-14T08:00:00', '2026-10-14T09:00:00', '2026-10-14T10:00:00',
     N'Éves portalanítás.', N'A vizsgálat rendben lezárult.', N'02:00:00:01:00:10', N'192.0.2.110'),
    (N'MINTA-011', N'SN-MINTA-011', N'Dell', N'PowerEdge R740', N'UZEMBEN', N'B02 rack', 1,
     '2025-11-05', N'Dell Technologies', '2025-10-29', 2550000, N'KITERJESZTETT', '2025-11-05', '2029-11-04',
     N'FIRMWARE', '2026-11-05T08:00:00', '2026-11-05T09:00:00', '2026-11-05T09:30:00',
     N'Firmware-ellenőrzés.', N'A verzió ellenőrizve.', N'02:00:00:01:00:11', N'192.0.2.111'),
    (N'MINTA-012', N'SN-MINTA-012', N'HPE', N'ProLiant DL380 Gen10', N'UZEMBEN', N'B02 rack', 3,
     '2025-12-01', N'Hewlett Packard Enterprise', '2025-11-25', 2890000, N'GYARTOI', '2025-12-01', '2028-11-30',
     N'TERVEZETT', '2026-12-01T08:00:00', '2026-12-01T09:00:00', '2026-12-01T10:00:00',
     N'Éves állapotfelmérés.', N'A vizsgálat rendben lezárult.', N'02:00:00:01:00:12', N'192.0.2.112'),
    (N'MINTA-013', N'SN-MINTA-013', N'Dell', N'PowerEdge R640', N'UZEMBEN', N'B02 rack', 5,
     '2025-12-15', N'Dell Technologies', '2025-12-08', 2450000, N'GYARTOI', '2025-12-15', '2028-12-14',
     N'FIRMWARE', '2026-12-15T08:00:00', '2026-12-15T09:00:00', '2026-12-15T09:30:00',
     N'Firmware-ellenőrzés.', N'A verzió naprakész.', N'02:00:00:01:00:13', N'192.0.2.113'),
    (N'MINTA-014', N'SN-MINTA-014', N'Cisco', N'Catalyst 9200L', N'UZEMBEN', N'A01 rack', 7,
     '2025-02-01', N'Cisco Systems', '2025-01-25', 1180000, N'GYARTOI', '2025-02-01', '2028-01-31',
     N'FIRMWARE', '2026-02-01T08:00:00', '2026-02-01T09:00:00', '2026-02-01T09:30:00',
     N'Ütemezett firmware-ellenőrzés.', N'A verzió naprakész.', N'02:00:00:01:00:14', N'192.0.2.114'),
    (N'MINTA-015', N'SN-MINTA-015', N'Synology', N'RS3621xs+', N'UZEMBEN', N'A02 rack', 7,
     '2025-03-01', N'Synology', '2025-02-22', 1740000, N'GYARTOI', '2025-03-01', '2028-02-29',
     N'TISZTITAS', '2026-03-01T08:00:00', '2026-03-01T09:00:00', '2026-03-01T10:00:00',
     N'Tárhelyállapot-ellenőrzés és tisztítás.', N'A vizsgálat rendben lezárult.', N'02:00:00:01:00:15', N'192.0.2.115'),
    (N'MINTA-016', N'SN-MINTA-016', N'Fortinet', N'FortiGate 100F', N'UZEMBEN', N'B01 rack', 7,
     '2025-04-01', N'Fortinet', '2025-03-24', 1420000, N'KITERJESZTETT', '2025-04-01', '2029-03-31',
     N'FIRMWARE', '2026-04-01T08:00:00', '2026-04-01T09:00:00', '2026-04-01T09:30:00',
     N'Ütemezett firmware-ellenőrzés.', N'A verzió naprakész.', N'02:00:00:01:00:16', N'192.0.2.116');

    INSERT INTO partner.Beszallito (Nev, Megjegyzes)
    SELECT v.Nev, N'Beszállítói rekord '
    FROM (SELECT DISTINCT BeszallitoNev AS Nev FROM @Minta) v
    WHERE NOT EXISTS (
        SELECT 1 FROM partner.Beszallito b WHERE b.Nev = v.Nev
    );

    INSERT INTO eszkoz.Eszkoz (
        LeltariSzam, Sorozatszam, ModellID, StatuszID, HelyID,
        RackPozicioKezdet, UzembehelyezesDatuma, Megjegyzes
    )
    SELECT
        d.LeltariSzam, d.Sorozatszam, m.ModellID, s.StatuszID, h.HelyID,
        d.RackPozicioKezdet, d.UzembehelyezesDatuma,
        N'Mintaeszköz'
    FROM @Minta d
    INNER JOIN torzs.Gyarto g ON g.Nev = d.GyartoNev
    INNER JOIN torzs.Modell m ON m.GyartoID = g.GyartoID AND m.Nev = d.ModellNev
    INNER JOIN torzs.Statusz s ON s.Kod = d.StatuszKod
    INNER JOIN infrastruktura.Hely h ON h.TelephelyID = @TelephelyID AND h.Nev = d.RackNev
    WHERE NOT EXISTS (
        SELECT 1 FROM eszkoz.Eszkoz e WHERE e.LeltariSzam = d.LeltariSzam
    );

    INSERT INTO eszkoz.Beszerzes (EszkozID, BeszallitoID, BeszerzesDatuma, BeszerzesiAr, Penznem, Megjegyzes)
    SELECT e.EszkozID, b.BeszallitoID, d.BeszerzesDatuma, d.BeszerzesiAr, 'HUF',
           N'Szemléltető ár'
    FROM @Minta d
    INNER JOIN eszkoz.Eszkoz e ON e.LeltariSzam = d.LeltariSzam
    INNER JOIN partner.Beszallito b ON b.Nev = d.BeszallitoNev
    WHERE NOT EXISTS (
        SELECT 1 FROM eszkoz.Beszerzes x WHERE x.EszkozID = e.EszkozID
    );

    INSERT INTO eszkoz.Garancia (EszkozID, GaranciaKezdete, GaranciaVege, GaranciaTipusID, Szolgaltato, Megjegyzes)
    SELECT e.EszkozID, d.GaranciaKezdete, d.GaranciaVege, gt.GaranciaTipusID,
           d.BeszallitoNev, N'Garanciaadat.'
    FROM @Minta d
    INNER JOIN eszkoz.Eszkoz e ON e.LeltariSzam = d.LeltariSzam
    INNER JOIN torzs.GaranciaTipus gt ON gt.Kod = d.GaranciaKod
    WHERE NOT EXISTS (
        SELECT 1
        FROM eszkoz.Garancia x
        WHERE x.EszkozID = e.EszkozID
          AND x.GaranciaKezdete = d.GaranciaKezdete
    );

    INSERT INTO eszkoz.Karbantartas (
        EszkozID, KarbantartasTipusID, BejelentesDatuma, KezdesDatuma,
        BefejezesDatuma, Leiras, Eredmeny, Koltseg, Penznem, Megjegyzes
    )
    SELECT e.EszkozID, kt.KarbantartasTipusID, d.BejelentesDatuma, d.KezdesDatuma,
           d.BefejezesDatuma, d.KarbantartasLeiras, d.KarbantartasEredmeny,
           0, 'HUF', N'Karbantartási esemény.'
    FROM @Minta d
    INNER JOIN eszkoz.Eszkoz e ON e.LeltariSzam = d.LeltariSzam
    INNER JOIN torzs.KarbantartasTipus kt ON kt.Kod = d.KarbantartasKod
    WHERE NOT EXISTS (
        SELECT 1
        FROM eszkoz.Karbantartas x
        WHERE x.EszkozID = e.EszkozID
          AND x.BejelentesDatuma = d.BejelentesDatuma
          AND x.KarbantartasTipusID = kt.KarbantartasTipusID
    );

    INSERT INTO halozat.HalozatiInterfesz (EszkozID, Nev, MACCim, SebessegMbps, Megjegyzes)
    SELECT e.EszkozID, N'LAN 1', d.MACCim, 1000, N'MAC-cím.'
    FROM @Minta d
    INNER JOIN eszkoz.Eszkoz e ON e.LeltariSzam = d.LeltariSzam
    WHERE NOT EXISTS (
        SELECT 1 FROM halozat.HalozatiInterfesz h WHERE h.MACCim = d.MACCim
    );

    INSERT INTO halozat.IPCim (HalozatiInterfeszID, IPCim, PrefixHossz, Elsodleges, Megjegyzes)
    SELECT h.HalozatiInterfeszID, d.IPCim, 24, 1, N'Dokumentációs IP; hálózatban nem használandó.'
    FROM @Minta d
    INNER JOIN halozat.HalozatiInterfesz h ON h.MACCim = d.MACCim
    WHERE NOT EXISTS (
        SELECT 1 FROM halozat.IPCim i WHERE i.IPCim = d.IPCim AND i.Aktiv = 1
    );

    COMMIT TRANSACTION;
    PRINT N'A adatok betöltése befejeződött.';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO
