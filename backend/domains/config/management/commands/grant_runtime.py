"""GRANT privilege runtime untuk peran aplikasi — dijalankan setelah migrasi.

Pemisahan migrator/runtime (ARCHITECTURE §4): tabel dimiliki mtx_migrator;
peran aplikasi hanya memperoleh SELECT/INSERT/UPDATE/DELETE + USAGE sequence.

Peran divalidasi sebagai identifier PostgreSQL sah (%I format() menangani
nama tabel/sequence); SQL dinamis di dalam DO block memakai format() PG,
bukan %-formatting Python (perbaikan: '%I' bentrok dengan operator % Python).

Konsolidasi beta-0.1 (port dari agent paralel): enumerasi SEMUA schema
non-sistem (public, radius, dst.) — versi lama hanya meng-grant schema
public sehingga runtime role kehilangan akses ke schema radius hasil
migrasi M3 (permission denied untuk proyeksi RADIUS pada DB milik migrator).
"""
import re

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import connection

_ROLE_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")

# Schema sistem yang tidak boleh di-grant ke peran aplikasi.
_SYSTEM_SCHEMAS = ("information_schema", "pg_catalog", "pg_toast")


class Command(BaseCommand):
    help = "GRANT privilege DML runtime bagi peran aplikasi (jalankan sebagai migrator)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--role", default="mtx_app")

    def handle(self, *args, **options) -> None:
        role = options["role"]
        if not _ROLE_RE.match(role):
            raise CommandError(f"Nama peran tidak sah: {role!r}")
        with connection.cursor() as cur:
            # Enumerasi semua schema non-sistem — schema baru hasil migrasi
            # (mis. radius) otomatis tercakup tanpa perlu daftar manual.
            cur.execute("SELECT nspname FROM pg_namespace WHERE nspname !~ '^pg_'")
            schemas = [r[0] for r in cur.fetchall() if r[0] not in _SYSTEM_SCHEMAS]
            for schema in schemas:
                cur.execute(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"')
            # format() PG memakai %I untuk identifier; literal peran dikutip
            # aman karena sudah lolos validasi regex di atas. Karena query
            # membawa parameter psycopg (%(schemas)s), %I wajib ditulis %%I
            # agar lolos unescape sebagai %I literal PostgreSQL.
            cur.execute(
                f"""
                DO $$
                DECLARE r RECORD;
                BEGIN
                  FOR r IN SELECT schemaname, tablename FROM pg_tables
                            WHERE schemaname = ANY(%(schemas)s) LOOP
                    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON %%I.%%I TO {role}',
                                   r.schemaname, r.tablename);
                  END LOOP;
                  FOR r IN SELECT schemaname, sequencename FROM pg_sequences
                            WHERE schemaname = ANY(%(schemas)s) LOOP
                    EXECUTE format('GRANT USAGE, SELECT ON %%I.%%I TO {role}',
                                   r.schemaname, r.sequencename);
                  END LOOP;
                END $$;
                """,
                {"schemas": schemas},
            )
        self.stdout.write(f"GRANT runtime untuk {role} (skema: {', '.join(sorted(schemas))}): OK")
