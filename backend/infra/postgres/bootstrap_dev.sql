-- Bootstrap role untuk deployment lokal/pengembangan (dev instance).
-- Produksi: instalasi.sh membuat peran dengan password kuat.
-- mtx_migrator : memilik skema (pemisahan migrator, ARCHITECTURE §4)
-- mtx_app      : runtime aplikasi — bukan superuser, NOBYPASSRLS
-- CATATAN: CREATEDB pada mtx_app hanya untuk pengujian lokal (pytest-django
-- membuat test database); RLS tetap berlaku penuh pada tabel yang dimiliki
-- peran mana pun karena FORCE ROW LEVEL SECURITY.

CREATE ROLE mtx_migrator LOGIN;
CREATE ROLE mtx_app LOGIN CREATEDB;

-- Dev database milik migrator; runtime memakai mtx_app.
CREATE DATABASE microtix OWNER mtx_migrator;

GRANT ALL PRIVILEGES ON DATABASE microtix TO mtx_app;
