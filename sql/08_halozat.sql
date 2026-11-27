USE EszkozNyilvantartas;
GO


------------------------
-- HÁLÓZATI INTERFÉSZ --
------------------------
CREATE TABLE halozat.HalozatiInterfesz
(
    HalozatiInterfeszID INT IDENTITY(1,1) NOT NULL,

    EszkozID INT NOT NULL,

    Nev NVARCHAR(100) NULL,
    MACCim CHAR(17) NULL,

    SebessegMbps INT NULL,

    Aktiv BIT NOT NULL
        CONSTRAINT DF_HalozatiInterfesz_Aktiv DEFAULT 1,

    Megjegyzes NVARCHAR(500) NULL,

    CONSTRAINT PK_HalozatiInterfesz
        PRIMARY KEY (HalozatiInterfeszID),

    CONSTRAINT FK_HalozatiInterfesz_Eszkoz
        FOREIGN KEY (EszkozID)
        REFERENCES eszkoz.Eszkoz(EszkozID),


    CONSTRAINT CK_HalozatiInterfesz_Sebesseg
        CHECK (SebessegMbps IS NULL OR SebessegMbps > 0)
);
GO


CREATE UNIQUE INDEX UX_HalozatiInterfesz_MACCim
    ON halozat.HalozatiInterfesz(MACCim)
    WHERE MACCim IS NOT NULL;
GO



------------
-- IP-CÍM --
------------

CREATE TABLE halozat.IPCim
(
    IPCimID INT IDENTITY(1,1) NOT NULL,

    HalozatiInterfeszID INT NOT NULL,

    IPCim NVARCHAR(45) NOT NULL,
    PrefixHossz TINYINT NULL,

    Elsodleges BIT NOT NULL
        CONSTRAINT DF_IPCim_Elsodleges DEFAULT 0,

    Aktiv BIT NOT NULL
        CONSTRAINT DF_IPCim_Aktiv DEFAULT 1,

    Megjegyzes NVARCHAR(500) NULL,

    CONSTRAINT PK_IPCim
        PRIMARY KEY (IPCimID),

    CONSTRAINT FK_IPCim_HalozatiInterfesz
        FOREIGN KEY (HalozatiInterfeszID)
        REFERENCES halozat.HalozatiInterfesz(HalozatiInterfeszID),

    CONSTRAINT CK_IPCim_Prefix
        CHECK
        (
            PrefixHossz IS NULL
            OR PrefixHossz BETWEEN 0 AND 128
        )
);
GO

CREATE UNIQUE INDEX UX_IPCim_Aktiv
    ON halozat.IPCim(IPCim)
    WHERE Aktiv = 1;
GO

CREATE UNIQUE INDEX UX_IPCim_Elsodleges_Aktiv
    ON halozat.IPCim(HalozatiInterfeszID)
    WHERE Aktiv = 1 AND Elsodleges = 1;
GO
