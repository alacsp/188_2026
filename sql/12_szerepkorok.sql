USE EszkozNyilvantartas;
GO
IF COL_LENGTH(N'biztonsag.Felhasznalo', N'Megtekinto') IS NULL
    ALTER TABLE biztonsag.Felhasznalo ADD Megtekinto BIT NOT NULL
        CONSTRAINT DF_Felhasznalo_Megtekinto DEFAULT 0 WITH VALUES;
GO
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name=N'CK_Felhasznalo_Szerepkor')
    ALTER TABLE biztonsag.Felhasznalo ADD CONSTRAINT CK_Felhasznalo_Szerepkor
        CHECK (Admin=0 OR Megtekinto=0);
GO
