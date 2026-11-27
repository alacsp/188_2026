USE EszkozNyilvantartas;
GO

----------------------------------------
-- INFRASTRUKTÚRA TÁBLÁK LÉTREHOZÁSA --
----------------------------------------

CREATE TABLE infrastruktura.Telephely
(
    TelephelyID INT IDENTITY(1,1) NOT NULL,
    Nev NVARCHAR(150) NOT NULL,
    Varos NVARCHAR(100) NULL,
    Cim NVARCHAR(250) NULL,
    Aktiv BIT NOT NULL
        CONSTRAINT DF_Telephely_Aktiv DEFAULT 1,

    CONSTRAINT PK_Telephely
        PRIMARY KEY (TelephelyID),

    CONSTRAINT UQ_Telephely_Nev
        UNIQUE (Nev)
);
GO

-----------------
-- TEREM TÁBLA --
-----------------
CREATE TABLE infrastruktura.Terem
(
    TeremID INT IDENTITY(1,1) NOT NULL,
    TelephelyID INT NOT NULL,
    Nev NVARCHAR(100) NOT NULL,
    Leiras NVARCHAR(500) NULL,
    Aktiv BIT NOT NULL
        CONSTRAINT DF_Terem_Aktiv DEFAULT 1,

    CONSTRAINT PK_Terem
        PRIMARY KEY (TeremID),

    CONSTRAINT FK_Terem_Telephely
        FOREIGN KEY (TelephelyID)
        REFERENCES infrastruktura.Telephely(TelephelyID),

    CONSTRAINT UQ_Terem
        UNIQUE (TelephelyID, Nev),
    
    CONSTRAINT UQ_Terem_Telephely_TeremID
        UNIQUE (TelephelyID, TeremID)
);
GO
----------------
-- HELY TÁBLA --
----------------
CREATE TABLE infrastruktura.Hely
(
    HelyID INT IDENTITY(1,1) NOT NULL,
    TelephelyID INT NOT NULL,
    TeremID INT NULL,

    HelyTipusID INT NOT NULL,          

    Nev NVARCHAR(150) NOT NULL,
    Leiras NVARCHAR(500) NULL,

    Aktiv BIT NOT NULL
        CONSTRAINT DF_Hely_Aktiv DEFAULT 1,

    CONSTRAINT PK_Hely
        PRIMARY KEY (HelyID),

    CONSTRAINT FK_Hely_Telephely
        FOREIGN KEY (TelephelyID)
        REFERENCES infrastruktura.Telephely(TelephelyID),

    CONSTRAINT FK_Hely_Terem
        FOREIGN KEY (TelephelyID, TeremID)
        REFERENCES infrastruktura.Terem(TelephelyID, TeremID),

    CONSTRAINT FK_Hely_HelyTipus
        FOREIGN KEY (HelyTipusID)
        REFERENCES torzs.HelyTipus(HelyTipusID),

    CONSTRAINT UQ_Hely
        UNIQUE (TelephelyID, Nev)
);
GO
----------------
-- RACK TÁBLA --
----------------
CREATE TABLE infrastruktura.Rack
(
    RackID INT IDENTITY(1,1) NOT NULL,
    HelyID INT NOT NULL,

    MagassagU TINYINT NOT NULL,

    CONSTRAINT PK_Rack
        PRIMARY KEY (RackID),

    CONSTRAINT FK_Rack_Hely
        FOREIGN KEY (HelyID)
        REFERENCES infrastruktura.Hely(HelyID),

    CONSTRAINT UQ_Rack_Hely
        UNIQUE (HelyID),

    CONSTRAINT CK_Rack_MagassagU
        CHECK (MagassagU > 0)
);
GO