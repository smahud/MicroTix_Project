-- Role DB untuk daemon FreeRADIUS (RAD-03 §4) — jalankan sebagai postgres.
-- Role hanya EXECUTE facade; tanpa SELECT/DML langsung pada tabel proyeksi.
CREATE ROLE radius_svc LOGIN PASSWORD :'radius_pw';

GRANT USAGE ON SCHEMA radius TO radius_svc;
REVOKE ALL ON ALL TABLES IN SCHEMA radius FROM radius_svc;
GRANT EXECUTE ON FUNCTION radius.facade_lookup_nas(text) TO radius_svc;
GRANT EXECUTE ON FUNCTION radius.facade_check(text, text) TO radius_svc;
GRANT EXECUTE ON FUNCTION radius.facade_reply(text, text) TO radius_svc;
-- radacct/radpostauth ditulis daemon (accounting) via tabel langsung:
-- beri INSERT/UPDATE terbatas hanya pada dua tabel itu (RAD-07).
GRANT INSERT, UPDATE, SELECT ON radius.radacct TO radius_svc;
GRANT INSERT, SELECT ON radius.radpostauth TO radius_svc;
-- Bootstrap lookup NAS (kebijakan nas_bootstrap; RAD-03 §4).
GRANT SELECT ON radius.nas TO radius_svc;
