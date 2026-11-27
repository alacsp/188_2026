USE EszkozNyilvantartas;
GO


---------------
-- BESZERZÉS --
---------------

CREATE TABLE eszkoz.Beszerzes
(
    BeszerzesID INT IDENTITY(1,1) NOT NULL,

    EszkozID INT NOT NULL,
    BeszallitoID INT NULL,

    BeszerzesDatuma DATE NULL,
    BeszerzesiAr DECIMAL(18,2) NULL,
    Penznem CHAR(3) NULL,

    SzamlaSzam NVARCHAR(100) NULL,
    MegrendelesSzam NVARCHAR(100) NULL,

    Megjegyzes NVARCHAR(500) NULL,

    CONSTRAINT PK_Beszerzes
        PRIMARY KEY (BeszerzesID),

    CONSTRAINT FK_Beszerzes_Eszkoz
        FOREIGN KEY (EszkozID)
        REFERENCES eszkoz.Eszkoz(EszkozID),

    CONSTRAINT FK_Beszerzes_Beszallito
        FOREIGN KEY (BeszallitoID)
        REFERENCES partner.Beszallito(BeszallitoID),

    CONSTRAINT CK_Beszerzes_Ar
        CHECK (BeszerzesiAr IS NULL OR BeszerzesiAr >= 0)
);
GO


--------------
-- GARANCIA --
--------------

CREATE TABLE eszkoz.Garancia
(
    GaranciaID INT IDENTITY(1,1) NOT NULL,

    EszkozID INT NOT NULL,

    GaranciaKezdete DATE NOT NULL,
    GaranciaVege DATE NOT NULL,
    GaranciaTipusID INT NULL,
    Szolgaltato NVARCHAR(150) NULL,
    Megjegyzes NVARCHAR(500) NULL,

    Aktiv BIT NOT NULL
        CONSTRAINT DF_Garancia_Aktiv DEFAULT 1,

    CONSTRAINT PK_Garancia
        PRIMARY KEY (GaranciaID),

    CONSTRAINT FK_Garancia_Eszkoz
        FOREIGN KEY (EszkozID)
        REFERENCES eszkoz.Eszkoz(EszkozID),

    CONSTRAINT FK_Garancia_GaranciaTipus
        FOREIGN KEY (GaranciaTipusID)
        REFERENCES torzs.GaranciaTipus(GaranciaTipusID),

    CONSTRAINT CK_Garancia_Datum
        CHECK (GaranciaVege >= GaranciaKezdete)
);
GO


------------------
-- KARBANTARTÁS --
------------------

CREATE TABLE eszkoz.Karbantartas
(
    KarbantartasID INT IDENTITY(1,1) NOT NULL,

    EszkozID INT NOT NULL,
    KarbantartasTipusID INT NOT NULL,
    BejelentesDatuma DATETIME2 NULL,
    KezdesDatuma DATETIME2 NULL,
    BefejezesDatuma DATETIME2 NULL,

    Leiras NVARCHAR(1000) NULL,
    Eredmeny NVARCHAR(1000) NULL,

    Koltseg DECIMAL(18,2) NULL,
    Penznem CHAR(3) NULL,

    Megjegyzes NVARCHAR(500) NULL,

    CONSTRAINT PK_Karbantartas
        PRIMARY KEY (KarbantartasID),

    CONSTRAINT FK_Karbantartas_Eszkoz
        FOREIGN KEY (EszkozID)
        REFERENCES eszkoz.Eszkoz(EszkozID),

    CONSTRAINT FK_Karbantartas_KarbantartasTipus
        FOREIGN KEY (KarbantartasTipusID)
        REFERENCES torzs.KarbantartasTipus(KarbantartasTipusID),

    CONSTRAINT CK_Karbantartas_Koltseg
        CHECK (Koltseg IS NULL OR Koltseg >= 0),

    CONSTRAINT CK_Karbantartas_Datum
        CHECK
        (
            BefejezesDatuma IS NULL
            OR KezdesDatuma IS NULL
            OR BefejezesDatuma >= KezdesDatuma
        )
);
GO