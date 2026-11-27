USE EszkozNyilvantartas;
GO


------------
-- ÜGYFÉL --
------------

CREATE TABLE partner.Ugyfel
(
    UgyfelID INT IDENTITY(1,1) NOT NULL,

    Nev NVARCHAR(200) NOT NULL,
    Adoszam NVARCHAR(50) NULL,
    KapcsolattartoNev NVARCHAR(150) NULL,
    KapcsolattartoEmail NVARCHAR(150) NULL,
    KapcsolattartoTelefon NVARCHAR(50) NULL,

    Aktiv BIT NOT NULL
        CONSTRAINT DF_Ugyfel_Aktiv DEFAULT 1,

    Megjegyzes NVARCHAR(500) NULL,

    CONSTRAINT PK_Ugyfel
        PRIMARY KEY (UgyfelID),

    CONSTRAINT UQ_Ugyfel_Nev
        UNIQUE (Nev)
);
GO


----------------
-- BESZÁLLÍTÓ --
----------------

CREATE TABLE partner.Beszallito
(
    BeszallitoID INT IDENTITY(1,1) NOT NULL,

    Nev NVARCHAR(200) NOT NULL,
    Adoszam NVARCHAR(50) NULL,

    KapcsolattartoNev NVARCHAR(150) NULL,
    KapcsolattartoEmail NVARCHAR(150) NULL,
    KapcsolattartoTelefon NVARCHAR(50) NULL,

    Aktiv BIT NOT NULL
        CONSTRAINT DF_Beszallito_Aktiv DEFAULT 1,

    Megjegyzes NVARCHAR(500) NULL,

    CONSTRAINT PK_Beszallito
        PRIMARY KEY (BeszallitoID),

    CONSTRAINT UQ_Beszallito_Nev
        UNIQUE (Nev)
);
GO


-------------------------------
-- ESZKÖZ - ÜGYFÉL KAPCSOLAT --
-------------------------------

CREATE TABLE partner.EszkozUgyfelKapcsolat
(
    EszkozUgyfelKapcsolatID INT IDENTITY(1,1) NOT NULL,

    EszkozID INT NOT NULL,
    UgyfelID INT NOT NULL,
    KapcsolatTipusID INT NOT NULL,

    ErvenyesTol DATE NOT NULL
        CONSTRAINT DF_EszkozUgyfelKapcsolat_ErvenyesTol
        DEFAULT CAST(GETDATE() AS DATE),

    ErvenyesIg DATE NULL,

    Megjegyzes NVARCHAR(500) NULL,

    CONSTRAINT PK_EszkozUgyfelKapcsolat
        PRIMARY KEY (EszkozUgyfelKapcsolatID),

    CONSTRAINT FK_EszkozUgyfelKapcsolat_Eszkoz
        FOREIGN KEY (EszkozID)
        REFERENCES eszkoz.Eszkoz(EszkozID),

    CONSTRAINT FK_EszkozUgyfelKapcsolat_Ugyfel
        FOREIGN KEY (UgyfelID)
        REFERENCES partner.Ugyfel(UgyfelID),

    CONSTRAINT FK_EszkozUgyfelKapcsolat_KapcsolatTipus
        FOREIGN KEY (KapcsolatTipusID)
        REFERENCES torzs.KapcsolatTipus(KapcsolatTipusID),

    CONSTRAINT CK_EszkozUgyfelKapcsolat_Datum
        CHECK
        (
            ErvenyesIg IS NULL
            OR ErvenyesIg >= ErvenyesTol
        )
);
GO