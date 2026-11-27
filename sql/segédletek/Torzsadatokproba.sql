SELECT * FROM torzs.Gyarto ORDER BY GyartoID;

SELECT * FROM torzs.EszkozTipus ORDER BY EszkozTipusID;

SELECT * FROM torzs.Statusz ORDER BY StatuszID;

SELECT * FROM torzs.HelyTipus ORDER BY HelyTipusID;

SELECT * FROM torzs.KarbantartasTipus; 

SELECT * FROM torzs.GaranciaTipus; 

SELECT * FROM torzs.KapcsolatTipus;

SELECT
    m.ModellID,
    g.Nev AS Gyarto,
    et.Nev AS EszkozTipus,
    m.Nev AS Modell,
    m.MagassagU
FROM torzs.Modell m
INNER JOIN torzs.Gyarto g
    ON m.GyartoID = g.GyartoID
INNER JOIN torzs.EszkozTipus et
    ON m.EszkozTipusID = et.EszkozTipusID
ORDER BY g.Nev, m.Nev;