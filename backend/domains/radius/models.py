"""Model domain RADIUS — proyeksi FreeRADIUS + cutover run (M3/M5).

Kontrak: docs/RADIUS.md §3 (model data), §4 (facade tenant), §10.2 (B0–B6).

- Tabel skema ``radius`` (nas/radcheck/radreply/radgroupreply/radusergroup/
  radacct/radpostauth) adalah PROYEKSI dari customers.AccessAccount — dibuat
  oleh migrasi SQL mentah (bukan Django) karena butuh skema non-default;
  model di sini ``managed=False`` murni untuk pembacaan ORM/tes.
- Sumber kebenaran tetap ``customers_access_account``; penulis proyeksi
  adalah domains/radius/projection.py dalam transaksi yang sama dengan
  service layer customers (RADIUS.md §1/§3).
- CutoverRun (tabel public radius_cutover_run) adalah state mesin cutover
  B0–B6 per router — tabel domain aplikasi biasa dengan RLS tenant.
"""
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone as dj_timezone


class Nas(models.Model):
    """Klien NAS terdaftar — trust anchor resolusi tenant (§4).

    nasname = alamat sumber paket (tunnel IP router); FreeRADIUS memvalidasi
    secret klien dari clients.conf hasil render reconciler, lalu facade
    memakai nasname untuk mengikat NAS terverifikasi → tenant pada transaksi
    yang sama. secret per router CSPRNG (§6.4), tidak dipakai ulang.
    """

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, db_column="tenant_id", related_name="radius_nas")
    router = models.ForeignKey("network.Router", on_delete=models.CASCADE, db_column="router_id", related_name="radius_nas")
    nasname = models.GenericIPAddressField()
    shortname = models.CharField(max_length=64, blank=True, default="")
    secret = models.CharField(max_length=128)
    type = models.CharField(max_length=32, default="other")
    applied_revision = models.IntegerField(default=0)
    desired_revision = models.IntegerField(default=1)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        managed = False
        db_table = 'radius"."nas'
        constraints = []  # UNIQUE dipasang via SQL mentah migrasi 0001


class RadCheck(models.Model):
    """Atribut kontrol per akun (Cleartext-Password/Auth-Type/Simultaneous-Use…)."""

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, db_column="tenant_id", related_name="radius_radcheck")
    account = models.ForeignKey("customers.AccessAccount", on_delete=models.CASCADE, db_column="account_id", related_name="radius_radcheck")
    username = models.CharField(max_length=64)
    attribute = models.CharField(max_length=64)
    scope = models.CharField(max_length=32, blank=True, default="")
    ordinal = models.IntegerField(default=0)
    op = models.CharField(max_length=8)
    value = models.CharField(max_length=253)

    class Meta:
        managed = False
        db_table = 'radius"."radcheck'


class RadReply(models.Model):
    """Atribut reply per akun (Mikrotik-Rate-Limit/Framed-Pool/Session-Timeout…)."""

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, db_column="tenant_id", related_name="radius_radreply")
    account = models.ForeignKey("customers.AccessAccount", on_delete=models.CASCADE, db_column="account_id", related_name="radius_radreply")
    username = models.CharField(max_length=64)
    attribute = models.CharField(max_length=64)
    scope = models.CharField(max_length=32, blank=True, default="")
    ordinal = models.IntegerField(default=0)
    op = models.CharField(max_length=8)
    value = models.CharField(max_length=253)

    class Meta:
        managed = False
        db_table = 'radius"."radreply'


class RadGroupReply(models.Model):
    """Atribut reply per grup — router_id NULL berlaku seluruh tenant (§3)."""

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, db_column="tenant_id", related_name="radius_radgroupreply")
    groupname = models.CharField(max_length=64)
    attribute = models.CharField(max_length=64)
    op = models.CharField(max_length=8)
    value = models.CharField(max_length=253)
    router = models.ForeignKey("network.Router", null=True, blank=True, on_delete=models.CASCADE, db_column="router_id", related_name="radius_radgroupreply")

    class Meta:
        managed = False
        db_table = 'radius"."radgroupreply'


class RadUserGroup(models.Model):
    """Keanggotaan grup per username (beta: tidak dipakai — group query kosong)."""

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, db_column="tenant_id", related_name="radius_radusergroup")
    username = models.CharField(max_length=64)
    groupname = models.CharField(max_length=64)
    priority = models.IntegerField(default=1)

    class Meta:
        managed = False
        db_table = 'radius"."radusergroup'


class RadAcct(models.Model):
    """Sesi accounting standar FreeRADIUS + tenant_id/router_id/service_id (§3)."""

    radacctid = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, db_column="tenant_id", related_name="radius_radacct")
    router = models.ForeignKey("network.Router", null=True, blank=True, on_delete=models.CASCADE, db_column="router_id", related_name="radius_radacct")
    service = models.ForeignKey("customers.Service", null=True, blank=True, on_delete=models.CASCADE, db_column="service_id", related_name="radius_radacct")
    acctsessionid = models.CharField(max_length=64)
    acctuniqueid = models.CharField(max_length=64)
    username = models.CharField(max_length=64)
    nasipaddress = models.GenericIPAddressField(null=True, blank=True)
    nasportid = models.CharField(max_length=32, blank=True, default="")
    acctstarttime = models.DateTimeField(null=True, blank=True)
    acctupdatetime = models.DateTimeField(null=True, blank=True)
    acctstoptime = models.DateTimeField(null=True, blank=True)
    acctsessiontime = models.IntegerField(null=True, blank=True)
    acctinputoctets = models.BigIntegerField(null=True, blank=True)
    acctoutputoctets = models.BigIntegerField(null=True, blank=True)
    calledstationid = models.CharField(max_length=50, blank=True, default="")
    callingstationid = models.CharField(max_length=50, blank=True, default="")
    framedipaddress = models.GenericIPAddressField(null=True, blank=True)
    acctterminatecause = models.CharField(max_length=32, blank=True, default="")
    servicetype = models.CharField(max_length=32, blank=True, default="")
    framedprotocol = models.CharField(max_length=32, blank=True, default="")
    acctdelaytime = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        managed = False
        db_table = 'radius"."radacct'


class RadPostAuth(models.Model):
    """Log hasil autentikasi — username+reply tanpa password, retensi §12."""

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, db_column="tenant_id", related_name="radius_radpostauth")
    username = models.CharField(max_length=64)
    reply = models.CharField(max_length=32)
    authdate = models.DateTimeField(default=dj_timezone.now)
    nas_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'radius"."radpostauth'


class CutoverRun(models.Model):
    """State mesin cutover per router — RADIUS.md §10.2 (B0–B6) sebagai data.

    Satu run dimajukan satu/langkah oleh job kind ``radius_cutover_step``;
    jendela observasi (B3 1800s, B4 86400s) bersifat NYATA — run berhenti
    pada state pending_observation dengan bukti jendela, dan dilanjutkan
    eksekusi job berikutnya setelah jendela terlewati. Bukti tiap tahap
    tersimpan pada evidence (JSON) — bukan klaim tanpa jejak.
    """

    class Phase(models.TextChoices):
        B0 = "B0"            # preflight
        B1 = "B1"            # parity auth sintetis via facade
        B2 = "B2"            # install klien RADIUS pada router
        B3 = "B3"            # canary + observasi 1800s
        B4 = "B4"            # shadow active + observasi 86400s
        B5 = "B5"            # authoritative
        B6 = "B6"            # rollback

    class State(models.TextChoices):
        IN_PROGRESS = "in_progress"
        PENDING_OBSERVATION = "pending_observation"
        AUTHORITATIVE = "authoritative"      # B5 selesai
        ROLLED_BACK = "rolled_back"          # B6 selesai
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="radius_cutover_runs", db_column="tenant_id")
    router = models.ForeignKey("network.Router", on_delete=models.CASCADE, related_name="radius_cutover_runs", db_column="router_id")
    phase = models.CharField(max_length=4, choices=Phase.choices, default=Phase.B0)
    state = models.CharField(max_length=24, choices=State.choices, default=State.IN_PROGRESS)
    evidence = models.JSONField(default=dict)
    created_by = models.ForeignKey("identity.User", null=True, on_delete=models.SET_NULL, db_column="created_by_id", related_name="radius_cutover_runs_created")
    created_at = models.DateTimeField(default=dj_timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "radius_cutover_run"
        indexes = [models.Index(fields=["tenant", "router", "state"], name="ix_covrun_tenant_router_state")]
