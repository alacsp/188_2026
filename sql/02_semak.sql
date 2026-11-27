
-----------------------
-- SÉMÁK LÉTREHOZÁSA --
-----------------------

USE EszkozNyilvantartas;

IF SCHEMA_ID(N'torzs') IS NULL
    EXEC(N'CREATE SCHEMA torzs');
GO

IF SCHEMA_ID(N'infrastruktura') IS NULL
    EXEC(N'CREATE SCHEMA infrastruktura');
GO

IF SCHEMA_ID(N'eszkoz') IS NULL
    EXEC(N'CREATE SCHEMA eszkoz');
GO

IF SCHEMA_ID(N'partner') IS NULL
    EXEC(N'CREATE SCHEMA partner');
GO

IF SCHEMA_ID(N'riport') IS NULL
    EXEC(N'CREATE SCHEMA riport');
GO

IF SCHEMA_ID(N'halozat') IS NULL
    EXEC(N'CREATE SCHEMA halozat');
GO