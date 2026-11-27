
USE EszkozNyilvantartas;
GO

--------------------------------------
-- POWER BI - ESZKÖZÖK RIPORTNÉZETE---
--------------------------------------

CREATE OR ALTER VIEW riport.vw_Eszkozok
AS
SELECT
    e.EszkozID,
    e.LeltariSzam,
    e.Sorozatszam,

    g.Nev AS Gyarto,
    m.Nev AS Modell,
    et.Nev AS EszkozTipus,

    s.Nev AS Statusz,
    s.Kod AS StatuszKod,

    e.Aktiv,
    e.UzembehelyezesDatuma,

    t.Nev AS Telephely,
    tr.Nev AS Terem,
    h.Nev AS Hely,
    ht.Nev AS HelyTipus,

    e.RackPozicioKezdet,
    m.MagassagU AS EszkozMagassagU,
    r.MagassagU AS RackMagassagU

FROM eszkoz.Eszkoz AS e

INNER JOIN torzs.Modell AS m
    ON e.ModellID = m.ModellID

INNER JOIN torzs.Gyarto AS g
    ON m.GyartoID = g.GyartoID

INNER JOIN torzs.EszkozTipus AS et
    ON m.EszkozTipusID = et.EszkozTipusID

INNER JOIN torzs.Statusz AS s
    ON e.StatuszID = s.StatuszID

LEFT JOIN infrastruktura.Hely AS h
    ON e.HelyID = h.HelyID

LEFT JOIN torzs.HelyTipus AS ht
    ON h.HelyTipusID = ht.HelyTipusID

LEFT JOIN infrastruktura.Telephely AS t
    ON h.TelephelyID = t.TelephelyID

LEFT JOIN infrastruktura.Terem AS tr
    ON h.TeremID = tr.TeremID

LEFT JOIN infrastruktura.Rack AS r
    ON h.HelyID = r.HelyID;
GO
