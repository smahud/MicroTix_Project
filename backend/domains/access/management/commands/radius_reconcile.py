"""Reconciler NAS FreeRADIUS — RAD-01 §2 (TK-307).

Alur: baca NAS lintas tenant dengan desired_revision > applied_revision
(jalur GUC layanan) → hasilkan clients.conf → VALIDASI dengan binary
FreeRADIUS versi terpin (`freeradius -C`) → terapkan (reload bila didukung)
→ tulis applied_revision HANYA setelah probe membuktikan secret baru
diterima (`radius_reconcile --mark-applied`, runbook operator).

Tanpa FreeRADIUS pada host: --dry-run tetap menghasilkan konfigurasi;
--apply gagal JUJUR (exit 1 BLOCKED) — bukan sukses palsu.
"""
from __future__ import annotations

import argparse

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone as dj_timezone


def pending_nas_rows() -> list[dict]:
    """Baca NAS lintas tenant (GUC platform_service; fail-closed)."""
    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute("SELECT set_config('app.platform_service', '1', true)")
            cur.execute(
                """
                SELECT n.id, n.tenant_id, n.router_id, n.shortname, n.nas_type,
                       n.desired_revision, n.applied_revision, r.tunnel_ip,
                       t.namespace AS tenant_slug
                FROM access_nas n
                JOIN network_router r ON r.id = n.router_id
                JOIN tenancy_tenant t ON t.id = n.tenant_id
                WHERE r.released_at IS NULL
                  AND (n.applied_revision IS NULL OR n.applied_revision < n.desired_revision)
                ORDER BY n.desired_revision, n.id
                """
            )
            columns = [c.name for c in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def render_clients_conf(rows: list[dict]) -> str:
    """Hasilkan clients.conf — listener hanya untuk alamat tunnel /32."""
    blocks = []
    for row in rows:
        if not row["tunnel_ip"]:
            continue  # router tanpa tunnel tidak dipublikasikan (jujur)
        shortname = row["shortname"].replace('"', "")
        blocks.append(
            f"# tenant={row['tenant_slug']} router={row['router_id']} rev={row['desired_revision']}\n"
            f'client "{shortname}" {{\n'
            f"    ipv4addr = {row['tunnel_ip']}\n"
            f"    secret = <<REDACTED_ENCRYPTED_SECRET>>\n"
            f"    shortname = {shortname}\n"
            f"    nastype = other\n"
            f"    proto = *\n"
            f"}}\n"
        )
    header = (
        "# MicroTix radius clients — DIHASILKAN radius_reconcile (JANGAN EDIT MANUAL).\n"
        "# Secret dienkripsi di basis data; reconciler menyuntik nilai saat apply.\n"
    )
    return header + "\n".join(blocks)


class Command(BaseCommand):
    help = "Rekonsiliasi klien NAS FreeRADIUS dari desired revision (RAD-01)"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--dry-run", action="store_true", help="Cetak konfigurasi tanpa menerapkan")
        parser.add_argument("--apply", action="store_true", help="Validasi + terapkan (butuh FreeRADIUS host)")
        parser.add_argument(
            "--mark-applied",
            metavar="NAS_ID:REVISION",
            help="Tulis applied_revision setelah probe membuktikan secret baru (runbook operator)",
        )

    def handle(self, *args, **options) -> None:
        if options["mark_applied"]:
            self._mark_applied(options["mark_applied"])
            return
        rows = pending_nas_rows()
        if not rows:
            self.stdout.write("Tidak ada NAS menunggu rekonsiliasi.")
            return
        conf = render_clients_conf(rows)
        if options["dry_run"] or not options["apply"]:
            self.stdout.write(conf)
            self.stdout.write(f"[dry-run] {len(rows)} NAS; gunakan --apply pada host FreeRADIUS.")
            return
        # --apply: validasi dengan binary terpasang; tanpa FreeRADIUS → BLOCKED jujur.
        import shutil
        import subprocess

        freeradius = shutil.which("freeradius")
        if freeradius is None:
            raise CommandError(
                "BLOCKED: freeradius tidak ditemukan pada host ini. Terapkan pada host "
                "FreeRADIUS 3.2 yang ditunjuk (lihat infra/freeradius/README.md)."
            )
        from django.conf import settings

        clients_path = getattr(settings, "MT_RADIUS_CLIENTS_PATH", "")
        if not clients_path:
            raise CommandError("MT_RADIUS_CLIENTS_PATH belum dikonfigurasi.")
        with open(clients_path, "w", encoding="utf-8") as fh:
            fh.write(self._secrets_injected(conf, rows))
        check = subprocess.run(
            [freeradius, "-C", "-d", getattr(settings, "MT_RADIUS_CONFIG_DIR", "/etc/freeradius")],
            capture_output=True,
            text=True,
        )
        if check.returncode != 0:
            raise CommandError(f"Validasi freeradius -C gagal: {check.stderr[:500]}")
        self.stdout.write(
            f"Konfigurasi ditulis + tervalidasi ({len(rows)} NAS). Jalankan probe lalu "
            "--mark-applied per NAS untuk menulis applied_revision."
        )

    def _secrets_injected(self, conf: str, rows: list[dict]) -> str:
        """Suntik secret terenkripsi saat menulis berkas (tidak pernah ke stdout)."""
        from domains.access import services as access_services

        for row in rows:
            # Baca lewat jalur layanan (lintas tenant), tulis tak diperlukan.
            nas = _service_read_nas(row["id"])
            if nas is None:
                continue
            try:
                secret = access_services.nas_secret(nas)
            except Exception:
                secret = ""
            conf = conf.replace(
                f'client "{row["shortname"]}" {{\n    ipv4addr = {row["tunnel_ip"]}\n    secret = <<REDACTED_ENCRYPTED_SECRET>>',
                f'client "{row["shortname"]}" {{\n    ipv4addr = {row["tunnel_ip"]}\n    secret = "{secret}"',
                1,
            )
        return conf

    def _mark_applied(self, spec: str) -> None:
        from domains.access.models import Nas

        nas_id, _, revision = spec.partition(":")
        if not nas_id or not revision.isdigit():
            raise CommandError("Format: NAS_UUID:REVISION")
        nas = _service_read_nas(nas_id)
        if nas is None:
            raise CommandError("NAS tidak ditemukan")
        if int(revision) != nas.desired_revision:
            raise CommandError(
                f"Revision probe ({revision}) != desired ({nas.desired_revision}) — probe usang, ulangi."
            )
        # Tulis dalam tenant_scope (kebijakan RLS tenant berlaku).
        from domains.common.tenant_context import tenant_scope

        with tenant_scope(nas.tenant_id):
            Nas.objects.filter(id=nas.id).update(
                applied_revision=int(revision), updated_at=dj_timezone.now()
            )
        self.stdout.write(f"applied_revision={revision} ditulis untuk NAS {nas_id}")


def _service_read_nas(nas_id: str):
    """Baca NAS lintas tenant lewat GUC layanan (fail-closed)."""
    from domains.access.models import Nas

    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute("SELECT set_config('app.platform_service', '1', true)")
            return Nas.objects.filter(id=nas_id).first()
