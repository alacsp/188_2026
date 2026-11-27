USE master;
GO
IF DB_ID(N'EszkozNyilvantartas') IS NOT NULL
    THROW 51000, N'Az adatbazis mar letezik.', 1;
GO
CREATE DATABASE EszkozNyilvantartas;
GO
