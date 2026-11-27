-------------------------------
-- ESZKÖZ TÁBLÁK LÉTREHOZÁSA --
-------------------------------

USE EszkozNyilvantartas;
GO

------------------
-- ESZKÖZ TÁBLA --
------------------

CREATE TABLE eszkoz.Eszkoz
(
    EszkozID INT IDENTITY(1,1) NOT NULL,

    LeltariSzam NVARCHAR(50) NOT NULL,
    Sorozatszam NVARCHAR(100) NULL,

    ModellID INT NOT NULL,
    StatuszID INT NOT NULL,

    HelyID INT NULL,
    RackPozicioKezdet TINYINT NULL,

    UzembehelyezesDatuma DATE NULL,

    Megjegyzes NVARCHAR(1000) NULL,

    Aktiv BIT NOT NULL
        CONSTRAINT DF_Eszkoz_Aktiv DEFAULT 1,

    CONSTRAINT PK_Eszkoz
        PRIMARY KEY (EszkozID),

    CONSTRAINT UQ_Eszkoz_LeltariSzam
        UNIQUE (LeltariSzam),

    CONSTRAINT FK_Eszkoz_Modell
        FOREIGN KEY (ModellID)
        REFERENCES torzs.Modell(ModellID),

    CONSTRAINT FK_Eszkoz_Statusz
        FOREIGN KEY (StatuszID)
        REFERENCES torzs.Statusz(StatuszID),

    CONSTRAINT FK_Eszkoz_Hely
        FOREIGN KEY (HelyID)
        REFERENCES infrastruktura.Hely(HelyID),

    CONSTRAINT CK_Eszkoz_RackPozicio
        CHECK (RackPozicioKezdet IS NULL OR RackPozicioKezdet > 0)
);
GO
CREATE UNIQUE INDEX UX_Eszkoz_Sorozatszam
    ON eszkoz.Eszkoz(Sorozatszam)
    WHERE Sorozatszam IS NOT NULL;
GO


---------------------------
-- ESZKÖZ MOZGATÁS TÁBLa --
---------------------------


CREATE TABLE eszkoz.EszkozMozgas
(
    EszkozMozgasID INT IDENTITY(1,1) NOT NULL,

    EszkozID INT NOT NULL,

    RegiHelyID INT NULL,
    UjHelyID INT NULL,

    RegiRackPozicio TINYINT NULL,
    UjRackPozicio TINYINT NULL,

    MozgasDatuma DATETIME2 NOT NULL
        CONSTRAINT DF_EszkozMozgas_MozgasDatuma
        DEFAULT SYSDATETIME(),

    Megjegyzes NVARCHAR(500) NULL,

    CONSTRAINT PK_EszkozMozgas
        PRIMARY KEY (EszkozMozgasID),

    CONSTRAINT FK_EszkozMozgas_Eszkoz
        FOREIGN KEY (EszkozID)
        REFERENCES eszkoz.Eszkoz(EszkozID),

    CONSTRAINT FK_EszkozMozgas_RegiHely
        FOREIGN KEY (RegiHelyID)
        REFERENCES infrastruktura.Hely(HelyID),

    CONSTRAINT FK_EszkozMozgas_UjHely
        FOREIGN KEY (UjHelyID)
        REFERENCES infrastruktura.Hely(HelyID),

    CONSTRAINT CK_EszkozMozgas_RegiRackPozicio
        CHECK (RegiRackPozicio IS NULL OR RegiRackPozicio > 0),

    CONSTRAINT CK_EszkozMozgas_UjRackPozicio
        CHECK (UjRackPozicio IS NULL OR UjRackPozicio > 0),

    CONSTRAINT CK_EszkozMozgas_Hely
        CHECK
        (
            RegiHelyID IS NOT NULL
            OR UjHelyID IS NOT NULL
        )
);
GO