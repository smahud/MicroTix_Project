"""GRANT privilege runtime untuk peran aplikasi — dijalankan setelah migrasi.

Pemisahan migrator/runtime (ARCHITECTURE §4): tabel dimiliki mtx_migrator;
peran aplikasi hanya memperoleh SELECT/INSERT/UPDATE/DELETE + USAGE sequence.

Fix 2026-11-05: SQL sebelumnya memakai %-formatting Python di atas string yang
memuat %I (placeholder format() PostgreSQL) → ValueError saat dieksekusi pada
PostgreSQL nyata. Sekarang identifier peran divalidasi regex lalu disisipkan
sebagai literal terkotak; %I tidak lagi disentuh Python.
"""
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

_ROLE_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


class Command(BaseCommand):
    help = "GRANT privilege DML runtime bagi peran aplikasi (jalankan sebagai migrator)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--role", default="mtx_app")

    def handle(self, *args, **options) -> None:
        role = options["role"]
        if not _ROLE_RE.fullmatch(role):
            raise CommandError(f"Nama peran tidak sah: {role!r}")
        with connection.cursor() as cur:
            # Skema aplikasi: public (inti) + radius (proyeksi FreeRADIUS, M3).
            # Skema sistem (pg_*/information_schema) dikecualikan implisit oleh
            # filter pg_tables + daftar skema eksplisit.
            cur.execute(
                "SELECT nspname FROM pg_namespace WHERE nspname IN ('public', 'radius')"
            )
            schemas = [r[0] for r in cur.fetchall()]
            for schema in schemas:
                cur.execute(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"')
            # GRANT per tabel/urutan — dibangun di sisi server agar aman untuk
            # identifier apa pun; nama peran sudah tervalidasi regex di atas.
            cur.execute(
                f"""
                DO $$
                DECLARE r RECORD;
                BEGIN
                  FOR r IN SELECT schemaname, tablename FROM pg_tables
                           WHERE schemaname = ANY(%(schemas)s) LOOP
                    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON %%I.%%I TO %%I',
                                   r.schemaname, r.tablename, %(role)s);
                  END LOOP;
                  FOR r IN SELECT schemaname, sequencename FROM pg_sequences
                           WHERE schemaname = ANY(%(schemas)s) LOOP
                    EXECUTE format('GRANT USAGE, SELECT ON %%I.%%I TO %%I',
                                   r.schemaname, r.sequencename, %(role)s);
                  END LOOP;
                END $$;
                """,
                {"role": role, "schemas": schemas},
            )
        self.stdout.write(f"GRANT runtime untuk {role} (skema: {', '.join(schemas) or '-'}): OK")
