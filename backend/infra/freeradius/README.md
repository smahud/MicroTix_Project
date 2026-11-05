# FreeRADIUS 3.2 — konfigurasi MicroTix (RAD-01/RAD-02)

Berkas di direktori ini adalah TEMPLATE untuk deployment FreeRADIUS nyata
pada host yang ditunjuk. Mereka TIDAK dipasang otomatis oleh installer
sebelum gate R1 jaringan (G1) terpenuhi — `make test-radius` jujur BLOCKED
tanpa daemon nyata.

## Topologi (RAD-01)

- FreeRADIUS 3.2 (patch keamanan terkini), `rlm_sql` PostgreSQL.
- Bind HANYA pada antarmuka tunnel WireGuard (`wg0`, 100.127.0.1), UDP 1812/1813.
- UDP 3799 (Disconnect/CoA) hanya dari /32 server — dikonfigurasi eksplisit.
- Satu NAS/router: alamat sumber tunnel unik + secret CSPRNG unik
  (dikelola `radius_reconcile`; lihat `backend/domains/access`).
- Role DB `radius_svc`: EXECUTE facade `radius.facade_*` SAJA; tanpa DML
  langsung pada tabel proyeksi (RAD-03 §4).

## Pemasangan (host Debian 13, saat gate diaktifkan)

```bash
apt-get install -y freeradius freeradius-postgresql
install -d -o freerad -g freerad /etc/freeradius/3.0/mods-config/files/microtix

# 1) Skema + facade sudah dibuat migrasi aplikasi (radius.*).
# 2) Role DB khusus daemon (jalankan sebagai postgres):
psql -f postgres/radius_role.sql microtix
# 3) Modul SQL → salin sql-microtix ke mods-available + symlink enable,
#    sesuaikan kredensial radius_svc lewat env/berkas 600 milik freerad.
# 4) clients.conf DIHASILKAN `manage.py radius_reconcile --apply`
#    (validasi freeradius -C dulu; secret disuntik, tidak dicetak).
# 5) Site default → ambil site-microtix (bind wg0 + message-authenticator).
freeradius -C -d /etc/freeradius/3.0   # wajib lulus sebelum restart
systemctl restart freeradius
```

## Verifikasi fungsional (RAD-14; jalankan dari host lab)

1. Daemon hidup: `systemctl is-active freeradius`.
2. SQL backend: `radtest` dengan NAS test terdaftar.
3. Credential salah ditolak; benar diterima (PAP → CHAP → MS-CHAPv2).
4. Tenant A tidak melihat konteks B (facade mengikat tenant dari NAS IP).
5. Accounting tersimpan per tenant (`radius.radacct`).
6. Simultaneous-Use bekerja (lock per tenant+account).
7. Atribut reply benar (Mikrotik-Rate-Limit, Framed-IP-Address/Pool).
8. Restart daemon tidak menghilangkan konfigurasi committed.

Tanpa langkah ini, status integrasi RADIUS = implemented/verified_local
untuk proyeksi+facade, dan BLOCKED untuk verified_lab — jangan klaim
sebaliknya (docs/ACCEPTANCE.md §5).
