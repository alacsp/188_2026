-- Meglévő adatbázison is futtatható, adatot nem töröl.
USE EszkozNyilvantartas;
GO
IF SCHEMA_ID(N'biztonsag') IS NULL EXEC(N'CREATE SCHEMA biztonsag');
GO
IF OBJECT_ID(N'biztonsag.Felhasznalo', N'U') IS NULL
CREATE TABLE biztonsag.Felhasznalo (
    FelhasznaloID INT IDENTITY PRIMARY KEY,
    Nev NVARCHAR(100) NOT NULL UNIQUE,
    JelszoHash VARCHAR(250) NOT NULL,
    Admin BIT NOT NULL DEFAULT 0,
    Aktiv BIT NOT NULL DEFAULT 1,
    Hibak INT NOT NULL DEFAULT 0,
    Zarolva DATETIME2 NULL,
    ResetHash VARCHAR(64) NULL,
    ResetLejar DATETIME2 NULL,
    Verzio INT NOT NULL DEFAULT 1
);
GO
