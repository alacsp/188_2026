-----------------------------
-- TÖRZSTÁBLÁK LÉTREHOZÁSA --
-----------------------------

USE EszkozNyilvantartas;
GO

------------------
-- GYÁRTÓ TÁBLA --
------------------
CREATE TABLE torzs.Gyarto
(
    GyartoID INT IDENTITY(1,1) NOT NULL,
    Nev NVARCHAR(100) NOT NULL,
    Aktiv BIT NOT NULL 
    CONSTRAINT DF_Gyarto_Aktiv DEFAULT 1,
    CONSTRAINT PK_Gyarto PRIMARY KEY (GyartoID),
    CONSTRAINT UQ_Gyarto_Nev UNIQUE (Nev)
);
GO

------------------------
-- ESZKÖZ TÍPUS TÁBLA --
------------------------

CREATE TABLE torzs.EszkozTipus
(
    EszkozTipusID INT IDENTITY(1,1) NOT NULL,
    Nev NVARCHAR(100) NOT NULL,
    Leiras NVARCHAR(500) NULL,
    Aktiv BIT NOT NULL 
    CONSTRAINT DF_EszkozTipus_Aktiv DEFAULT 1,
    CONSTRAINT PK_EszkozTipus PRIMARY KEY (EszkozTipusID),
    CONSTRAINT UQ_EszkozTipus_Nev UNIQUE (Nev)
);
GO

------------------------
-- MODELL TÍPUS TÁBLA --
------------------------

CREATE TABLE torzs.Modell
(
    ModellID INT IDENTITY(1,1) NOT NULL,
    GyartoID INT NOT NULL,
    EszkozTipusID INT NOT NULL,
    Nev NVARCHAR(150) NOT NULL,
    MagassagU TINYINT NULL,
    Aktiv BIT NOT NULL 
    CONSTRAINT DF_Modell_Aktiv DEFAULT 1,
    CONSTRAINT PK_Modell PRIMARY KEY (ModellID),
    CONSTRAINT FK_Modell_Gyarto
        FOREIGN KEY (GyartoID)
        REFERENCES torzs.Gyarto(GyartoID),
    CONSTRAINT FK_Modell_EszkozTipus
        FOREIGN KEY (EszkozTipusID)
        REFERENCES torzs.EszkozTipus(EszkozTipusID),
    CONSTRAINT UQ_Modell UNIQUE (GyartoID, Nev)
);
GO

-------------------------
-- STÁTUSZ TÍPUS TÁBLA --
-------------------------

CREATE TABLE torzs.Statusz
(
    StatuszID INT IDENTITY(1,1) NOT NULL,
    Kod NVARCHAR(30) NOT NULL,
    Nev NVARCHAR(100) NOT NULL,
    Leiras NVARCHAR(500) NULL,
    Aktiv BIT NOT NULL 
    CONSTRAINT DF_Statusz_Aktiv DEFAULT 1,
    CONSTRAINT PK_Statusz PRIMARY KEY (StatuszID),
    CONSTRAINT UQ_Statusz_Kod UNIQUE (Kod),
    CONSTRAINT UQ_Statusz_Nev UNIQUE (Nev)
);
GO

----------------------
-- HELY TÍPUS TÁBLA --
----------------------

CREATE TABLE torzs.HelyTipus
(
    HelyTipusID INT IDENTITY(1,1) NOT NULL,
    Kod NVARCHAR(30) NOT NULL,
    Nev NVARCHAR(100) NOT NULL,
    Leiras NVARCHAR(500) NULL,
    Aktiv BIT NOT NULL
    CONSTRAINT DF_HelyTipus_Aktiv DEFAULT 1,
    CONSTRAINT PK_HelyTipus PRIMARY KEY (HelyTipusID),
    CONSTRAINT UQ_HelyTipus_Kod UNIQUE (Kod),
    CONSTRAINT UQ_HelyTipus_Nev UNIQUE (Nev)
);
GO

------------------------------
-- KARBANTARTÁS TÍPUS TÁBLA --
------------------------------

CREATE TABLE torzs.KarbantartasTipus (
    KarbantartasTipusID INT IDENTITY(1,1) NOT NULL,
    Kod NVARCHAR(30) NOT NULL,
    Nev NVARCHAR(100) NOT NULL,
    Aktiv BIT NOT NULL 
    CONSTRAINT DF_KarbantartasTipus_Aktiv DEFAULT 1,
    CONSTRAINT PK_KarbantartasTipus PRIMARY KEY (KarbantartasTipusID),
    CONSTRAINT UQ_KarbantartasTipus_Kod UNIQUE (Kod),
    CONSTRAINT UQ_KarbantartasTipus_Nev UNIQUE (Nev)
);
GO

--------------------------
-- GARANCIA TÍPUS TÁBLA --
--------------------------

CREATE TABLE torzs.GaranciaTipus (
    GaranciaTipusID INT IDENTITY(1,1) NOT NULL,
    Kod NVARCHAR(30) NOT NULL,
    Nev NVARCHAR(100) NOT NULL,
    Aktiv BIT NOT NULL 
    CONSTRAINT DF_GaranciaTipus_Aktiv DEFAULT 1,
    CONSTRAINT PK_GaranciaTipus PRIMARY KEY (GaranciaTipusID),
    CONSTRAINT UQ_GaranciaTipus_Kod UNIQUE (Kod),
    CONSTRAINT UQ_GaranciaTipus_Nev UNIQUE (Nev)
);
GO
---------------------------
-- KAPCSOLAT TÍPUS TÁBLA --
---------------------------

CREATE TABLE torzs.KapcsolatTipus (
    KapcsolatTipusID INT IDENTITY(1,1) NOT NULL,
    Kod NVARCHAR(30) NOT NULL,
    Nev NVARCHAR(100) NOT NULL,
    Aktiv BIT NOT NULL 
    CONSTRAINT DF_KapcsolatTipus_Aktiv DEFAULT 1,
    CONSTRAINT PK_KapcsolatTipus PRIMARY KEY (KapcsolatTipusID),
    CONSTRAINT UQ_KapcsolatTipus_Kod UNIQUE (Kod),
    CONSTRAINT UQ_KapcsolatTipus_Nev UNIQUE (Nev)
);
GO