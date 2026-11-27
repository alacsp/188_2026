--------------------
--- Jogusultságok---
--------------------

USE EszkozNyilvantartas;
GO
IF DATABASE_PRINCIPAL_ID(N'EszkozApiJog') IS NULL
    CREATE ROLE EszkozApiJog AUTHORIZATION dbo;
GO
IF DATABASE_PRINCIPAL_ID(N'EszkozApiFuttato') IS NULL
    CREATE USER EszkozApiFuttato WITHOUT LOGIN;
GO
IF NOT EXISTS (
    SELECT 1 FROM sys.database_role_members
    WHERE role_principal_id=DATABASE_PRINCIPAL_ID(N'EszkozApiJog')
      AND member_principal_id=DATABASE_PRINCIPAL_ID(N'EszkozApiFuttato')
)
    ALTER ROLE EszkozApiJog ADD MEMBER EszkozApiFuttato;
GO
GRANT SELECT, INSERT, UPDATE ON SCHEMA::torzs TO EszkozApiJog;
GRANT SELECT, INSERT, UPDATE ON SCHEMA::eszkoz TO EszkozApiJog;
GRANT SELECT, INSERT, UPDATE ON SCHEMA::partner TO EszkozApiJog;
GRANT SELECT, INSERT, UPDATE ON SCHEMA::halozat TO EszkozApiJog;
GRANT SELECT, INSERT, UPDATE ON SCHEMA::infrastruktura TO EszkozApiJog;
GRANT DELETE ON OBJECT::infrastruktura.Rack TO EszkozApiJog;
GRANT SELECT, INSERT, UPDATE ON OBJECT::biztonsag.Felhasznalo TO EszkozApiJog;
GO

