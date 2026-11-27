:ON ERROR EXIT
----------------------------------------------------------
-- TELJES ADATBÁZIS TELEPÍTÉS
-- Az EszkozNyilvantartas adatbázis teljes
-- struktúrájának felépítése a rész-scriptekből.
--
-- FONTOS: SSMS-ben SQLCMD Mode használata szükséges.
-- A fájlt az sql mappából kell futtatni, hogy a relatív
-- :r hivatkozások feloldhatók legyenek.
-----------------------------------------------------------

PRINT N'01 - Adatbázis létrehozása';
:r .\01_adatbazis.sql

PRINT N'02 - Sémák létrehozása';
:r .\02_semak.sql

PRINT N'03 - Törzstáblák létrehozása';
:r .\03_torzstabla.sql

PRINT N'04 - Infrastruktúra táblák létrehozása';
:r .\04_infrastruktura_tabla.sql

PRINT N'05 - Eszköz táblák létrehozása';
:r .\05_eszkoz_tabla.sql

PRINT N'06 - Partner táblák létrehozása';
:r .\06_partner_tabla.sql

PRINT N'07 - Beszerzés és karbantartás táblák létrehozása';
:r .\07_beszerzes_karbantartas.sql

PRINT N'08 - Hálózati táblák létrehozása';
:r .\08_halozat.sql

PRINT N'09 - Törzsadatok feltöltése';
:r .\09_torzsadatok.sql

:r .\10_powerbi_nezetek.sql

PRINT N'11 - Felhasználói fiókok';
:r .\11_felhasznalok.sql

PRINT N'12 - Három szerepkör';
:r .\12_szerepkorok.sql

PRINT N'13 - Korlátozott API adatbázis-jogosultságok';
:r .\13_api_jogosultsagok.sql

PRINT N'A tiszta adatbazis telepitese sikeres.';
