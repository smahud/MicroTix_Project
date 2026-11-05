"""GRANT privilege runtime untuk peran aplikasi — dijalankan setelah migrasi.

Pemisahan migrator/runtime (ARCHITECTURE §4): tabel dimiliki mtx_migrator;
peran aplikasi hanya memperoleh SELECT/INSERT/UPDATE/DELETE + USAGE sequence.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "GRANT privilege DML runtime bagi peran aplikasi (jalankan sebagai migrator)"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--role", default="mtx_app")

    def handle(self, *args, **options) -> None:
        role = options["role"]
        with connection.cursor() as cur:
            cur.execute("GRANT USAGE ON SCHEMA public TO " + role)
            cur.execute(
                """
                DO $$
                DECLARE r RECORD;
                BEGIN
                  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname='public' LOOP
                    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON public.%I TO %I', r.tablename, '%(role)s');
                  END LOOP;
                  FOR r IN SELECT sequencename FROM pg_sequences WHERE schemaname='public' LOOP
                    EXECUTE format('GRANT USAGE, SELECT ON public.%I TO %I', r.sequencename, '%(role)s');
                  END LOOP;
                END $$;
                """
                % {"role": role}
            )
        self.stdout.write(f"GRANT runtime untuk {role}: OK")
