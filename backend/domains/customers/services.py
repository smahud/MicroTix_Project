"""Layanan domain customers — provisioning, kredensial, CSV, migrasi (M4).

Aturan utama (ARCHITECTURE §4/§5/§7, RADIUS §3/§10.1, ROUTEROS §3):
- AccessAccount sumber kebenaran AAA; secret_ref terenkripsi SecretBox.
- Kuota layanan: committed (Service aktif) + reservasi pending vs batas paket.
- Commit CSV/migrasi hanya DB (Tahap A) — router tidak pernah disentuh.
- Mode beta yang belum tersedia gagal JUJUR (dependency_unavailable), bukan
  sukses palsu.
- Semua fungsi berjalan dalam tenant_scope pemanggil (view/job engine) dan
  transaksi atomik bersama pemanggil.
"""
from __future__ import annotations

import datetime
import hashlib
import unicodedata
import uuid

from django.db import transaction
from django.utils import timezone

from domains.common.crypto import SecretBox
from domains.common.envelope import ApiError
from domains.common.tenant_context import set_tenant_context
from domains.customers.models import (
    AccessAccount,
    CsvImport,
    Customer,
    MigrationAccountDecision,
    MigrationSession,
    Service,
)
from domains.jobs import engine
from domains.network.models import DiscoveryObject, DiscoverySnapshot, Router

# Batas username RADIUS.md §3: ≤64 karakter dan ≤64 byte UTF-8, tanpa spasi
# tepi, tanpa karakter kontrol; dibanding persis (case-sensitive).
USERNAME_MAX_CHARS = 64
USERNAME_MAX_BYTES = 64

CSV_MAX_ROWS = 5000
CSV_PREVIEW_ROWS = 10

# Layanan yang tidak lagi menghitung kuota (kapasitas dibebaskan).
NON_COUNTED_LIFECYCLE = (Service.Lifecycle.TERMINATED, Service.Lifecycle.ARCHIVED)


# ---------------------------------------------------------------------------
# Validasi username (RADIUS.md §3)


def validate_username(username: object, *, field: str = "username") -> str:
    """Validasi username akses; tolak 422 dengan kode alasan stabil."""
    if not isinstance(username, str) or username == "":
        raise ApiError.validation({field: [{"code": "required", "message": "Username wajib diisi"}]})
    if username != username.strip():
        raise ApiError.validation(
            {field: [{"code": "whitespace", "message": "Username tidak boleh diawali/diakhiri spasi"}]}
        )
    if len(username) > USERNAME_MAX_CHARS or len(username.encode("utf-8")) > USERNAME_MAX_BYTES:
        raise ApiError.validation(
            {field: [{"code": "max_length", "message": f"Username maksimum {USERNAME_MAX_CHARS} karakter dan {USERNAME_MAX_BYTES} byte UTF-8"}]}
        )
    if any(unicodedata.category(ch) == "Cc" or ord(ch) == 0x7F for ch in username):
        raise ApiError.validation(
            {field: [{"code": "control_char", "message": "Username tidak boleh memuat karakter kontrol"}]}
        )
    return username


# ---------------------------------------------------------------------------
# Kode unik tenant (CUS-/SVC- + 6 heks, cek bentrokan)


def _generate_code(tenant_id, model, prefix: str, field: str) -> str:
    for _ in range(5):
        code = f"{prefix}-{uuid.uuid4().hex[:6].upper()}"
        if not model.objects.filter(tenant_id=tenant_id, **{field: code}).exists():
            return code
    raise ApiError.conflict()


# ---------------------------------------------------------------------------
# Kuota layanan (SUB-02): committed + reservasi pending vs batas paket.
# Catatan: subscriptions.services._committed("services") masih 0 (M1 jujur);
# penghitungan committed milik domain ini — Service aktif dihitung di sini.


def services_limit(tenant_id) -> int | None:
    """Batas efektif layanan paket (lisensi; Platinum plafon operasional)."""
    from domains.subscriptions.models import Subscription

    sub = Subscription.objects.select_related("plan").get(tenant=tenant_id)
    plan = sub.plan
    if plan.services_limit is not None:
        return plan.services_limit
    return plan.services_opcap


def committed_services(tenant_id) -> int:
    """committed_counted_accounts: layanan non-terminal tenant."""
    return Service.objects.filter(tenant_id=tenant_id).exclude(lifecycle__in=NON_COUNTED_LIFECYCLE).count()


def _pending_service_reservations(tenant_id) -> int:
    """Reservasi services pending; kedaluwarsa ditandai (SUB-02)."""
    from domains.subscriptions.models import QuotaReservation

    QuotaReservation.objects.filter(
        tenant_id=tenant_id,
        resource=QuotaReservation.Resource.SERVICES,
        state=QuotaReservation.State.PENDING,
        expires_at__lte=timezone.now(),
    ).update(state=QuotaReservation.State.EXPIRED, expires_at=timezone.now())
    return QuotaReservation.objects.filter(
        tenant_id=tenant_id, resource=QuotaReservation.Resource.SERVICES, state=QuotaReservation.State.PENDING
    ).count()


def reserve_services_quota(tenant_id, units: int = 1):
    """Cek + reservasi kuota layanan atomik; lewat batas → 409 quota_exceeded.

    Penghitungan: committed (domain ini) + reservasi pending (subscriptions).
    Reservasi dibuat via subscriptions.services.reserve agar lintas proses
    terkoordinasi; commit/release mengikuti siklus SUB-02.
    """
    from domains.subscriptions import services as subs_services

    if units <= 0:
        return None
    limit = services_limit(tenant_id)
    if limit is not None:
        pending = _pending_service_reservations(tenant_id)
        if committed_services(tenant_id) + pending + units > limit:
            raise ApiError.conflict("quota_exceeded", "error.quota_exceeded")
    return subs_services.reserve(tenant_id, "services", units)


def quota_snapshot(tenant_id) -> tuple[int, int | None]:
    return committed_services(tenant_id), services_limit(tenant_id)


# ---------------------------------------------------------------------------
# Provisioning layanan (POST /services)


def _clean_str(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _parse_date(value: object, field: str):
    if value in (None, ""):
        return None
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value))
    except ValueError:
        raise ApiError.validation({field: [{"code": "invalid", "message": "Format tanggal harus YYYY-MM-DD"}]}) from None


@transaction.atomic
def provision_service_draft(tenant, payload: dict, *, actor=None) -> Service:
    """Buat Customer + Service(draft) + AccessAccount (opsional) atomik.

    Input toleran terhadap bentuk UI (customer_name/contact/final_choice) dan
    bentuk spesifikasi (display_name/phone). Akun akses dibuat hanya bila
    username diberikan; password opsional (tanpa password → credential_state
    unknown, jujur — bukan ready palsu).
    """
    tenant_id = tenant.id
    body = payload if isinstance(payload, dict) else {}

    # --- pelanggan: existing via customer_code, atau baru ---
    customer_code = _clean_str(body.get("customer_code"))
    if customer_code:
        customer = Customer.objects.filter(tenant_id=tenant_id, customer_code=customer_code).first()
        if customer is None:
            raise ApiError.not_found()
    else:
        display_name = _clean_str(body.get("customer_name") or body.get("display_name"))
        if not display_name:
            raise ApiError.validation(
                {"customer_name": [{"code": "required", "message": "Nama pelanggan wajib diisi"}]}
            )
        customer = Customer.objects.create(
            tenant_id=tenant_id,
            display_name=display_name[:120],
            customer_code=_generate_code(tenant_id, Customer, "CUS", "customer_code"),
            phone=_clean_str(body.get("phone") or body.get("contact"))[:32],
            email=_clean_str(body.get("email"))[:255],
            address=_clean_str(body.get("address"))[:255],
        )

    # --- field layanan ---
    kind = _clean_str(body.get("kind")) or Service.Kind.PPPOE
    if kind not in Service.Kind.values:
        raise ApiError.validation({"kind": [{"code": "choice", "message": "kind harus pppoe atau hotspot"}]})
    service_code = _clean_str(body.get("service_code")) or _generate_code(tenant_id, Service, "SVC", "service_code")
    if Service.objects.filter(tenant_id=tenant_id, service_code=service_code).exists():
        raise ApiError.conflict()
    router = None
    router_id = _clean_str(body.get("router_id"))
    if router_id:
        router = Router.objects.filter(id=router_id, tenant_id=tenant_id, released_at=None).first()
        if router is None:
            raise ApiError.validation(
                {"router_id": [{"code": "invalid", "message": "Router tidak ditemukan"}]}
            )
    start_date = _parse_date(body.get("start_date"), "start_date")

    # --- kuota + layanan (draft) ---
    reservation = reserve_services_quota(tenant_id, 1)
    service = Service.objects.create(
        tenant_id=tenant_id,
        customer=customer,
        service_code=service_code,
        package_name=_clean_str(body.get("package_name"))[:120],
        kind=kind,
        lifecycle=Service.Lifecycle.DRAFT,
        router=router,
        start_date=start_date,
        notes=_clean_str(body.get("notes")),
    )

    # --- akun akses (opsional pada draft) ---
    username = body.get("username")
    final_choice = _clean_str(body.get("final_choice")) or "draft"
    if username is None and final_choice in ("create_account", "create_and_activate"):
        raise ApiError.validation(
            {"username": [{"code": "required", "message": "Username wajib untuk membuat akun akses"}]}
        )
    if username is not None:
        username = validate_username(username)
        if AccessAccount.objects.filter(tenant_id=tenant_id, username=username).exists():
            # UNIQUE(tenant, username) — satu namespace per tenant (RADIUS §3).
            raise ApiError.conflict()
        account = AccessAccount.objects.create(tenant_id=tenant_id, service=service, username=username, kind=kind)
        password = body.get("password")
        if password:
            set_password(account, str(password))

    if reservation is not None:
        from domains.subscriptions import services as subs_services

        subs_services.commit_reservation(reservation)

    _audit(
        tenant_id,
        "customers.service_created",
        actor=actor,
        target_type="service",
        target_id=service.id,
        target_display=service.service_code,
        payload={"lifecycle": service.lifecycle, "kind": service.kind},
    )
    return service


# ---------------------------------------------------------------------------
# Kredensial (RAD-05)


def set_password(account: AccessAccount, password: str) -> None:
    """Enkripsi password ke secret_ref; credential_state ready; bump revision.

    Berjalan dalam transaksi pemanggil (rotasi = aksi terpisah, RADIUS §6.3).
    """
    if not password:
        raise ApiError.validation({"password": [{"code": "required", "message": "Password wajib diisi"}]})
    account.secret_ref = SecretBox.encrypt(password)
    account.credential_state = AccessAccount.CredentialState.READY
    account.revision += 1
    account.save(update_fields=["secret_ref", "credential_state", "revision", "updated_at"])


def reveal_password(account: AccessAccount) -> str:
    """Dekripsi secret_ref → password plaintext (sekali tampil; izin+reauth di view)."""
    if not account.secret_ref or account.credential_state != AccessAccount.CredentialState.READY:
        # credential_state unknown — tidak ada yang bisa direveal (jujur).
        raise ApiError.conflict()
    return SecretBox.decrypt_str(account.secret_ref)


# ---------------------------------------------------------------------------
# State akun akses: suspend ↔ active saja (disabled/expired izin lebih kuat)


_ACCOUNT_STATE_TRANSITIONS: dict[str, frozenset[str]] = {
    AccessAccount.State.ACTIVE: frozenset({AccessAccount.State.SUSPENDED}),
    AccessAccount.State.SUSPENDED: frozenset({AccessAccount.State.ACTIVE}),
    AccessAccount.State.DISABLED: frozenset(),
    AccessAccount.State.EXPIRED: frozenset(),
}


def set_account_state(account: AccessAccount, new_state: str, *, actor=None) -> AccessAccount:
    """Transisi state akun: hanya suspended↔active via API operasional.

    disabled/expired memerlukan alur/izin lebih kuat → 409 conflict.
    """
    if new_state not in (AccessAccount.State.SUSPENDED, AccessAccount.State.ACTIVE):
        raise ApiError.validation({"state": [{"code": "choice", "message": "state harus suspended atau active"}]})
    if new_state == account.state:
        return account  # idempoten
    allowed = _ACCOUNT_STATE_TRANSITIONS.get(account.state, frozenset())
    if new_state not in allowed:
        raise ApiError.conflict()
    account.state = new_state
    account.revision += 1
    account.save(update_fields=["state", "revision", "updated_at"])
    _audit(
        account.tenant_id,
        "customers.account_state_changed",
        actor=actor,
        target_type="access_account",
        target_id=account.id,
        target_display=account.username,
        payload={"state": new_state},
    )
    return account


# ---------------------------------------------------------------------------
# CSV import (U08): validasi sinkron + commit via job import_commit


def _row_error(row: int, field: str | None, reason_code: str, hint: str) -> dict:
    return {"row": row, "field": field, "reason_code": reason_code, "action_hint": hint}


def _validate_create_rows(tenant_id: str, rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Validasi baris mode create; kembalikan (indeks valid, row_errors).

    Username yang sudah ada di tenant BUKAN galat — dilewati saat commit
    (idempoten, dihitung unchanged).
    """
    errors: list[dict] = []
    valid_idx: list[int] = []
    seen: set[str] = set()
    for i, raw in enumerate(rows):
        row_no = i + 2  # baris 1 = header CSV (paritas perilaku adapter mock)
        row = raw if isinstance(raw, dict) else {}
        username = row.get("username")
        ok = True
        if not isinstance(username, str) or username == "":
            errors.append(_row_error(row_no, "username", "required", "Isi username atau hapus baris"))
            ok = False
        else:
            if username != username.strip():
                errors.append(_row_error(row_no, "username", "whitespace", "Hapus spasi di awal/akhir username"))
                ok = False
            elif len(username) > USERNAME_MAX_CHARS or len(username.encode("utf-8")) > USERNAME_MAX_BYTES:
                errors.append(_row_error(row_no, "username", "max_length", f"Username maksimum {USERNAME_MAX_CHARS} karakter/{USERNAME_MAX_BYTES} byte"))
                ok = False
            elif any(unicodedata.category(ch) == "Cc" or ord(ch) == 0x7F for ch in username):
                errors.append(_row_error(row_no, "username", "control_char", "Hapus karakter kontrol dari username"))
                ok = False
            elif username in seen:
                errors.append(_row_error(row_no, "username", "duplicate_in_file", "Username sama muncul lebih dari sekali dalam berkas"))
                ok = False
        kind = row.get("kind", "pppoe") or "pppoe"
        if not isinstance(kind, str) or kind not in Service.Kind.values:
            errors.append(_row_error(row_no, "kind", "choice", "kind harus pppoe atau hotspot"))
            ok = False
        if ok:
            seen.add(username)
            valid_idx.append(i)
    return valid_idx, errors


def _validate_link_rows(tenant_id: str, rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Validasi baris mode link: username harus sudah ada, service_code wajib."""
    errors: list[dict] = []
    valid_idx: list[int] = []
    for i, raw in enumerate(rows):
        row_no = i + 2
        row = raw if isinstance(raw, dict) else {}
        ok = True
        username = row.get("username")
        if not isinstance(username, str) or username == "":
            errors.append(_row_error(row_no, "username", "required", "Isi username atau hapus baris"))
            ok = False
        elif not AccessAccount.objects.filter(tenant_id=tenant_id, username=username).exists():
            errors.append(_row_error(row_no, "username", "account_not_found", "Akun akses dengan username ini belum ada"))
            ok = False
        service_code = row.get("service_code")
        if not isinstance(service_code, str) or service_code == "":
            errors.append(_row_error(row_no, "service_code", "required", "Isi service_code tujuan tautan"))
        elif not Service.objects.filter(tenant_id=tenant_id, service_code=service_code).exists():
            errors.append(_row_error(row_no, "service_code", "service_not_found", "Layanan dengan service_code ini tidak ditemukan"))
            ok = False
        if ok:
            valid_idx.append(i)
    return valid_idx, errors


def validate_csv(csv_import: CsvImport) -> dict:
    """Validasi sinkron → CsvValidationResult (kontrak); simpan ke draf."""
    if csv_import.mode in (CsvImport.Mode.DEVICE_MAPPING, CsvImport.Mode.PASSWORD_MIGRATION):
        # Mode fase berikutnya — jujur 503, bukan validasi palsu (§5).
        raise ApiError.unavailable()
    rows = csv_import.rows if isinstance(csv_import.rows, list) else []
    if csv_import.mode == CsvImport.Mode.LINK:
        valid_idx, errors = _validate_link_rows(str(csv_import.tenant_id), rows)
    else:
        valid_idx, errors = _validate_create_rows(str(csv_import.tenant_id), rows)
    result = {
        "total_rows": len(rows),
        "valid_rows": len(valid_idx),
        "error_rows": len(errors),
        "row_errors": errors,
        "preview": [r for r in rows if isinstance(r, dict)][:CSV_PREVIEW_ROWS],
    }
    csv_import.validation = result
    csv_import.state = CsvImport.State.VALIDATED
    csv_import.save(update_fields=["validation", "state"])
    return result


@transaction.atomic
def commit_csv(csv_import: CsvImport) -> dict:
    """Commit draf tervalidasi (dipanggil job import_commit): DB-only.

    - create: Customer+Service(draft)+AccessAccount per baris valid;
      (tenant, username) sudah ada → dilewati (unchanged), idempoten.
    - link: tautkan akun existing ke layanan (tanpa kuota baru).
    - mode lain: JobError dependency_unavailable — jujur, belum tersedia beta.
    """
    from domains.jobs.engine import JobError

    if csv_import.state == CsvImport.State.COMMITTED:
        # Replay job/commit ulang: kembalikan ringkasan yang sama (idempoten).
        return dict(csv_import.validation.get("commit_summary", {}))
    if csv_import.state != CsvImport.State.VALIDATED:
        raise JobError(code="not_validated", retryable=False, message="Draf belum divalidasi")

    rows = csv_import.rows if isinstance(csv_import.rows, list) else []
    if csv_import.mode == CsvImport.Mode.CREATE:
        summary = _commit_csv_create(csv_import, rows)
    elif csv_import.mode == CsvImport.Mode.LINK:
        summary = _commit_csv_link(csv_import, rows)
    else:
        raise JobError(
            code="dependency_unavailable",
            retryable=False,
            message="Mode impor ini belum tersedia pada beta (validasi tercatat, commit menyusul)",
        )
    csv_import.validation = {**csv_import.validation, "commit_summary": summary}
    csv_import.state = CsvImport.State.COMMITTED
    csv_import.committed_at = timezone.now()
    csv_import.save(update_fields=["validation", "state", "committed_at"])
    _audit(
        csv_import.tenant_id,
        "customers.csv_committed",
        target_type="csv_import",
        target_id=csv_import.id,
        target_display=csv_import.file_name,
        payload={"mode": csv_import.mode, **summary},
    )
    return summary


def _commit_csv_create(csv_import: CsvImport, rows: list[dict]) -> dict:
    tenant_id = csv_import.tenant_id
    valid_idx, _ = _validate_create_rows(str(tenant_id), rows)
    to_create: list[tuple[int, dict]] = []
    unchanged = 0
    for i in valid_idx:
        row = rows[i]
        username = row["username"]
        if AccessAccount.objects.filter(tenant_id=tenant_id, username=username).exists():
            unchanged += 1  # skip-existing → idempoten
        else:
            to_create.append((i, row))
    reservation = reserve_services_quota(tenant_id, len(to_create))
    for _, row in to_create:
        username = validate_username(row["username"])
        kind = row.get("kind") or Service.Kind.PPPOE
        display_name = _clean_str(row.get("customer_name")) or username
        customer = Customer.objects.create(
            tenant_id=tenant_id,
            display_name=display_name[:120],
            customer_code=_generate_code(tenant_id, Customer, "CUS", "customer_code"),
            phone=_clean_str(row.get("phone"))[:32],
            address=_clean_str(row.get("address"))[:255],
        )
        service = Service.objects.create(
            tenant_id=tenant_id,
            customer=customer,
            service_code=_generate_code(tenant_id, Service, "SVC", "service_code"),
            package_name=_clean_str(row.get("package"))[:120],
            kind=kind,
            lifecycle=Service.Lifecycle.DRAFT,
        )
        account = AccessAccount.objects.create(tenant_id=tenant_id, service=service, username=username, kind=kind)
        password = row.get("password")
        if isinstance(password, str) and password:
            set_password(account, password)
    if reservation is not None:
        from domains.subscriptions import services as subs_services

        subs_services.commit_reservation(reservation)
    return {"mode": "create", "created": len(to_create), "unchanged": unchanged}


def _commit_csv_link(csv_import: CsvImport, rows: list[dict]) -> dict:
    tenant_id = csv_import.tenant_id
    valid_idx, _ = _validate_link_rows(str(tenant_id), rows)
    linked = unchanged = 0
    for i in valid_idx:
        row = rows[i]
        account = AccessAccount.objects.filter(tenant_id=tenant_id, username=row["username"]).first()
        service = Service.objects.filter(tenant_id=tenant_id, service_code=row["service_code"]).first()
        if account is None or service is None:
            unchanged += 1  # race: hilang setelah validasi — lewati jujur
            continue
        if account.service_id == service.id:
            unchanged += 1
            continue
        account.service = service
        account.revision += 1
        account.save(update_fields=["service", "revision", "updated_at"])
        linked += 1
    return {"mode": "link", "linked": linked, "unchanged": unchanged}


# ---------------------------------------------------------------------------
# Migrasi Tahap A (RADIUS §10.1) — discovery/adopsi DB-only


@transaction.atomic
def start_migration(tenant, router: Router, *, actor=None) -> tuple[MigrationSession, object | None]:
    """Buat sesi migrasi + job discover_router (handler milik domain network).

    Bila handler discover_router belum terdaftar (domain network dikerjakan
    paralel oleh lead), sesi tetap dibuat dan job_id dikembalikan None secara
    jujur — tidak ada job palsu (engine.create_job menolak kind tanpa handler).
    """
    session = MigrationSession.objects.create(tenant_id=tenant.id, router=router, created_by=actor)
    job = None
    try:
        job = engine.create_job(
            tenant_id=tenant.id,
            kind="discover_router",
            actor=actor,
            router=router,
            payload={"session_id": str(session.id)},
        )
    except ValueError:
        job = None  # handler discover_router belum tersedia — endpoint jujur
    finally:
        # engine.create_job membuka tenant_scope BERSARANG yang saat keluar
        # mereset GUC app.tenant_id (session-level, tenant_context.finally) —
        # pulihkan konteks transaction-local agar penulisan lanjutan (audit)
        # tetap sah menurut RLS.
        from django.db import connection

        set_tenant_context(connection, tenant.id)
    _audit(
        tenant.id,
        "customers.migration_started",
        actor=actor,
        target_type="migration_session",
        target_id=session.id,
        target_display=router.display_name,
        payload={"router_id": str(router.id)},
    )
    return session, job


def conflict_group_id(usernames: list[str]) -> str:
    """ID grup stabil: sha256(username terurut)[:16] — dipakai URL resolusi."""
    canonical = "|".join(sorted(usernames))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def identity_conflict_groups(tenant_id) -> dict[str, dict]:
    """Grup kandidat konflik identitas lintas router tenant (snapshot terbaru).

    Grup = username sama case-insensitive pada >1 router berbeda (RADIUS
    §10.1.3: kandidat gabung struktural; sebelum S1–S4 hanya structural_match,
    belum klaim password sama). Objek adopted/ignored tidak diikutkan.
    """
    latest_ids = (
        DiscoverySnapshot.objects.filter(tenant_id=tenant_id, status=DiscoverySnapshot.Status.SUCCEEDED)
        .order_by("router_id", "-started_at")
        .distinct("router_id")
        .values_list("id", flat=True)
    )
    objects = (
        DiscoveryObject.objects.filter(snapshot_id__in=list(latest_ids))
        .exclude(state__in=(DiscoveryObject.ObjState.ADOPTED, DiscoveryObject.ObjState.IGNORED))
        .select_related("router")
    )
    grouped: dict[str, dict] = {}
    for obj in objects:
        key = obj.username.lower()
        group = grouped.setdefault(key, {"usernames": set(), "routers": {}, "objects": []})
        group["usernames"].add(obj.username)
        group["routers"][str(obj.router_id)] = obj.router.display_name
        group["objects"].append(obj)
    # Hanya grup dengan >1 router berbeda.
    return {
        conflict_group_id(sorted(g["usernames"])): {
            "usernames": sorted(g["usernames"]),
            "routers": g["routers"],
            "objects": g["objects"],
        }
        for g in grouped.values()
        if len(g["routers"]) > 1
    }


def resolve_conflict_group(session: MigrationSession, group_id: str, resolution: str, new_username: str = "") -> int:
    """Simpan keputusan Owner untuk seluruh objek grup → baris MigrationAccountDecision.

    keep_one mengecualikan sumber lain (tanpa menghapus); rename membuat
    identitas DB baru (new_username wajib unik tenant).
    """
    if resolution not in (
        MigrationAccountDecision.Decision.MERGE,
        MigrationAccountDecision.Decision.KEEP_ONE,
        MigrationAccountDecision.Decision.RENAME,
    ):
        raise ApiError.validation({"resolution": [{"code": "choice", "message": "resolution harus merge, keep_one, atau rename"}]})
    if resolution == MigrationAccountDecision.Decision.RENAME:
        new_username = validate_username(new_username or None)
        if AccessAccount.objects.filter(tenant_id=session.tenant_id, username=new_username).exists():
            raise ApiError.conflict()
    else:
        new_username = ""
    groups = identity_conflict_groups(session.tenant_id)
    group = groups.get(group_id)
    if group is None:
        raise ApiError.not_found()
    with transaction.atomic():
        for obj in group["objects"]:
            MigrationAccountDecision.objects.update_or_create(
                session=session,
                discovery_object=obj,
                tenant_id=session.tenant_id,
                defaults={"decision": resolution, "new_username": new_username},
            )
            # Objek konflik yang telah diputuskan → selected (wizard lanjut).
            if obj.state == DiscoveryObject.ObjState.CONFLICT:
                DiscoveryObject.objects.filter(id=obj.id).update(state=DiscoveryObject.ObjState.SELECTED)
        if session.state in (MigrationSession.State.DISCOVERED,):
            session.state = MigrationSession.State.RESOLVING
            session.save(update_fields=["state"])
    return len(group["objects"])


@transaction.atomic
def preview_migration_summary(session: MigrationSession, selected_ids: list[str] | None = None) -> dict:
    """Ringkasan MigrationSummaryCounts TANPA efek samping (untuk wizard U07).

    Cermin logika penghitungan commit_migration (kategori sama); dipanggil
    endpoint commit sebelum job dibuat agar UI langsung mendapat angka.
    Job commit_migration menghitung ulang nilai aktual dan menimpa counts.
    """
    tenant_id = session.tenant_id
    selected_set = {str(s) for s in selected_ids} if selected_ids is not None else None
    decisions = {str(d.discovery_object_id): d for d in session.decisions.all()}
    groups = identity_conflict_groups(tenant_id)
    conflict_member_ids: set[str] = set()
    for group in groups.values():
        conflict_member_ids.update(str(obj.id) for obj in group["objects"])

    counts = {"to_create": 0, "to_merge": 0, "unchanged": 0, "conflicts": 0, "quota_used": 0, "quota_limit": 0}
    to_adopt: list[DiscoveryObject] = []
    if session.snapshot_id is not None:
        objects = list(session.snapshot.discovery_objects.select_related("router").order_by("username", "id"))
        merge_decisions = 0
        for obj in objects:
            obj_id = str(obj.id)
            if selected_set is not None and obj_id not in selected_set:
                counts["unchanged"] += 1
                continue
            decision = decisions.get(obj_id)
            if decision is not None and decision.decision == MigrationAccountDecision.Decision.IGNORED:
                continue
            if obj_id in conflict_member_ids and (
                decision is None or decision.decision == MigrationAccountDecision.Decision.SELECTED
            ):
                counts["conflicts"] += 1
                continue
            if decision is not None and decision.decision == MigrationAccountDecision.Decision.MERGE:
                merge_decisions += 1
            to_adopt.append(obj)
        # keep_one: satu sumber per grup (urutan stabil).
        kept: list[DiscoveryObject] = []
        keep_one_seen: set[str] = set()
        for obj in to_adopt:
            decision = decisions.get(str(obj.id))
            if decision is not None and decision.decision == MigrationAccountDecision.Decision.KEEP_ONE:
                group_key = obj.username.lower()
                if group_key in keep_one_seen:
                    counts["unchanged"] += 1
                    continue
                keep_one_seen.add(group_key)
            kept.append(obj)
        to_adopt = kept
        # Username efektif (rename/merge kanonik) → hitung yang benar-benar baru.
        canonical = {gid: min(g["usernames"]) for gid, g in groups.items()}
        obj_group = {str(o.id): gid for gid, g in groups.items() for o in g["objects"]}
        effective: set[str] = set()
        for obj in to_adopt:
            decision = decisions.get(str(obj.id))
            if decision is not None and decision.decision == MigrationAccountDecision.Decision.RENAME and decision.new_username:
                effective.add(decision.new_username)
            elif decision is not None and decision.decision == MigrationAccountDecision.Decision.MERGE:
                effective.add(canonical[obj_group[str(obj.id)]])
            else:
                effective.add(obj.username)
        for username in effective:
            if not AccessAccount.objects.filter(tenant_id=tenant_id, username=username).exists():
                counts["to_create"] += 1
        counts["to_merge"] = merge_decisions
    used, limit = quota_snapshot(tenant_id)
    counts["quota_used"] = used
    counts["quota_limit"] = limit if limit is not None else 0
    return counts


def commit_migration(session: MigrationSession, *, selected_ids: list[str] | None = None) -> dict:
    """Commit adopsi DB-only (dipanggil job commit_migration) — RADIUS §10.1.5.

    Membuat/menggabungkan Customer+Service(provisioned)+AccessAccount untuk
    objek terpilih; credential_state tetap unknown tanpa sumber password
    (slice ini). Router TIDAK diubah (Tahap A; bukti: tidak ada DeviceOperation).
    Objek default diadopsi semua, kecuali: ignored, grup konflik tanpa resolusi,
    atau tidak masuk selected_ids eksplisit (bila dikirim).
    """
    from domains.jobs.engine import JobError

    if session.state == MigrationSession.State.COMMITTED:
        return dict(session.counts or {})  # replay idempoten
    if session.snapshot_id is None:
        raise JobError(code="no_snapshot", retryable=False, message="Sesi belum memiliki snapshot discovery")
    if session.state not in (
        MigrationSession.State.DISCOVERED,
        MigrationSession.State.RESOLVING,
        MigrationSession.State.READY_TO_COMMIT,
    ):
        raise JobError(code="conflict", retryable=False, message=f"State sesi tidak sah untuk commit: {session.state}")

    tenant_id = session.tenant_id
    selected_set = {str(s) for s in selected_ids} if selected_ids is not None else None
    decisions = {str(d.discovery_object_id): d for d in session.decisions.all()}
    groups = identity_conflict_groups(tenant_id)
    # Objek mana pun yang masuk grup konflik (untuk pengecualian tanpa resolusi).
    conflict_member_ids: set[str] = set()
    for group in groups.values():
        conflict_member_ids.update(str(obj.id) for obj in group["objects"])

    objects = list(
        session.snapshot.discovery_objects.select_related("router").order_by("username", "id")
    )
    to_adopt: list[DiscoveryObject] = []
    counts = {"to_create": 0, "to_merge": 0, "unchanged": 0, "conflicts": 0, "quota_used": 0, "quota_limit": 0}
    merge_decisions = 0
    for obj in objects:
        obj_id = str(obj.id)
        if selected_set is not None and obj_id not in selected_set:
            counts["unchanged"] += 1  # tidak dipilih operator
            continue
        decision = decisions.get(obj_id)
        if decision is not None and decision.decision == MigrationAccountDecision.Decision.IGNORED:
            continue
        if obj_id in conflict_member_ids and (decision is None or decision.decision == MigrationAccountDecision.Decision.SELECTED):
            counts["conflicts"] += 1  # butuh resolusi — tidak diadopsi (needs_review)
            continue
        if decision is not None and decision.decision == MigrationAccountDecision.Decision.MERGE:
            merge_decisions += 1
        to_adopt.append(obj)

    # keep_one: pertahankan satu sumber per grup (urutan stabil username,id);
    # sumber lain dikecualikan, TIDAK dihapus (RADIUS §10.1).
    kept: list[DiscoveryObject] = []
    keep_one_seen: set[str] = set()
    for obj in to_adopt:  # sudah terurut (username, id)
        decision = decisions.get(str(obj.id))
        if decision is not None and decision.decision == MigrationAccountDecision.Decision.KEEP_ONE:
            group_key = obj.username.lower()
            if group_key in keep_one_seen:
                counts["unchanged"] += 1
                continue
            keep_one_seen.add(group_key)
        kept.append(obj)
    to_adopt = kept

    # Username efektif: rename → new_username; merge → username kanonik grup
    # (min leksikografis, deterministik); selain itu username objek.
    canonical: dict[str, str] = {gid: min(g["usernames"]) for gid, g in groups.items()}
    obj_group: dict[str, str] = {}
    for gid, g in groups.items():
        for o in g["objects"]:
            obj_group[str(o.id)] = gid

    effective: dict[str, list[DiscoveryObject]] = {}
    for obj in to_adopt:
        decision = decisions.get(str(obj.id))
        if decision is not None and decision.decision == MigrationAccountDecision.Decision.RENAME and decision.new_username:
            username = decision.new_username
        elif decision is not None and decision.decision == MigrationAccountDecision.Decision.MERGE:
            username = canonical[obj_group[str(obj.id)]]
        else:
            username = obj.username
        effective.setdefault(username, []).append(obj)

    # Cek duplikasi username efektif yang akan dibuat (mis. dua rename sama).
    for username in effective:
        if not AccessAccount.objects.filter(tenant_id=tenant_id, username=username).exists():
            counts["to_create"] += 1
    reservation = reserve_services_quota(tenant_id, counts["to_create"])

    for username, objs in effective.items():
        account = AccessAccount.objects.filter(tenant_id=tenant_id, username=username).first()
        if account is None:
            first = objs[0]
            customer = Customer.objects.create(
                tenant_id=tenant_id,
                display_name=username[:120],  # nama pelanggan sejati diisi operator belakangan
                customer_code=_generate_code(tenant_id, Customer, "CUS", "customer_code"),
            )
            service = Service.objects.create(
                tenant_id=tenant_id,
                customer=customer,
                service_code=_generate_code(tenant_id, Service, "SVC", "service_code"),
                # Profil router dipetakan ke paket free-text (katalog paket fase berikut).
                package_name=(first.profile or "")[:120],
                kind=first.kind,
                lifecycle=Service.Lifecycle.PROVISIONED,
                router=session.router,
                notes=(first.comment or "")[:500],
            )
            AccessAccount.objects.create(
                tenant_id=tenant_id,
                service=service,
                username=username,
                kind=first.kind,
                # disabled=yes → state=disabled (RADIUS §10.1.4; ditinjau operator).
                state=AccessAccount.State.DISABLED if first.disabled_on_router else AccessAccount.State.ACTIVE,
                mac_lock=(first.caller_id or None) if (first.caller_id or "").strip() else None,
                static_ip=first.remote_address,
                # Tanpa sumber password pada slice ini → credential_state unknown (jujur).
            )
        else:
            counts["unchanged"] += 1
        for obj in objs:
            if obj.state != DiscoveryObject.ObjState.ADOPTED:
                DiscoveryObject.objects.filter(id=obj.id).update(state=DiscoveryObject.ObjState.ADOPTED)

    if reservation is not None:
        from domains.subscriptions import services as subs_services

        subs_services.commit_reservation(reservation)

    counts["to_merge"] = merge_decisions
    used, limit = quota_snapshot(tenant_id)
    counts["quota_used"] = used
    counts["quota_limit"] = limit if limit is not None else 0
    session.counts = counts
    session.state = MigrationSession.State.COMMITTED
    session.committed_at = timezone.now()
    session.save(update_fields=["counts", "state", "committed_at"])
    _audit(
        tenant_id,
        "customers.migration_committed",
        target_type="migration_session",
        target_id=session.id,
        target_display=session.router.display_name,
        payload=dict(counts),
    )
    return counts


# ---------------------------------------------------------------------------
# Audit (payload tersanitasi otomatis — password tidak pernah masuk)


def _audit(tenant_id, action_code: str, *, actor=None, target_type: str = "", target_id=None, target_display: str = "", payload: dict | None = None) -> None:
    from domains.audit.models import record

    record(
        tenant_id=tenant_id,
        action_code=action_code,
        actor_display=getattr(actor, "full_name", "") or getattr(actor, "email", "") if actor is not None else "",
        actor_id=getattr(actor, "id", None) if actor is not None else None,
        target_type=target_type,
        target_id=str(target_id) if target_id else "",
        target_display=target_display,
        payload=payload or {},
    )
