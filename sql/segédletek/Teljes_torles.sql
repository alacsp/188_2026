--------------------------------------------------------
-- TELJES ADATBÁZIS TÖRLÉS
-- FIGYELEM: Az EszkozNyilvantartas adatbázist és annak
--           minden adatát véglegesen törli.
--------------------------------------------------------

USE master;
GO

IF DB_ID(N'EszkozNyilvantartas') IS NOT NULL
BEGIN
ALTER DATABASE EszkozNyilvantartas
SET SINGLE_USER
WITH ROLLBACK IMMEDIATE;
DROP DATABASE EszkozNyilvantartas;
END;