"""GRANT privilege runtime untuk peran aplikasi — dijalankan setelah migrasi.

Pemisahan migrator/runtime (ARCHITECTURE §4): tabel dimiliki mtx_migrator;
peran aplikasi hanya memperoleh SELECT/INSERT/UPDATE/DELETE + USAGE sequence.

Peran divalidasi sebagai identifier PostgreSQL sah (%I format() menangani
nama tabel/sequence); SQL dinamis di dalam DO block memakai format() PG,
bukan %-formatting Python (perbaikan: '%I' bentrok dengan operator % Python).
"""
import re

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import connection

_ROLE_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


class Command(BaseCommand):
    help = "GRANT privilege DML runtime bagi peran aplikasi (jalankan sebagai migrator)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--role", default="mtx_app")

    def handle(self, *args, **options) -> None:
        role = options["role"]
        if not _ROLE_RE.match(role):
            raise CommandError(f"Nama peran tidak sah: {role!r}")
        with connection.cursor() as cur:
            cur.execute(f'GRANT USAGE ON SCHEMA public TO "{role}"')
            # format() PG memakai %I untuk identifier; literal peran dikutip
            # aman karena sudah lolos validasi regex di atas.
            cur.execute(
                f"""
                DO $$
                DECLARE r RECORD;
                BEGIN
                  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname='public' LOOP
                    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON public.%I TO {role}', r.tablename);
                  END LOOP;
                  FOR r IN SELECT sequencename FROM pg_sequences WHERE schemaname='public' LOOP
                    EXECUTE format('GRANT USAGE, SELECT ON public.%I TO {role}', r.sequencename);
                  END LOOP;
                END $$;
                """
            )
        self.stdout.write(f"GRANT runtime untuk {role}: OK")
