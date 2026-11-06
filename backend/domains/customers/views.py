"""API customers — services, akun akses, CSV import, migrasi (M4).

Endpoint mengikuti live adapter apps/web/src/api/live/adapter.ts persis;
bentuk respons mengikuti apps/web/src/api/contracts.ts. Semua list memakai
paginasi kursor (sort_key,id) dan semua mutasi Idempotency-Key (§5) —
kecuali reveal-credentials (rahasia tidak pernah di-cache, no-store).
"""
from __future__ import annotations

import uuid as uuid_mod

from django.db.models import Exists, OuterRef, Prefetch, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from domains.common.envelope import ApiError
from domains.common.idempotency import idempotent
from domains.common.pagination import decode_cursor, encode_cursor, page_response, parse_limit
from domains.common.views import TenantApiView
from domains.customers import services
from domains.customers.models import (
    AccessAccount,
    CsvImport,
    MigrationSession,
    Service,
)
from domains.jobs import engine
from domains.network.models import DiscoveryObject, Router


def _body(request: Request) -> dict:
    data = getattr(request, "data", None)
    return data if isinstance(data, dict) else {}


def _validate_choice(field: str, value: str, choices) -> str:
    if value not in choices:
        raise ApiError.validation({field: [{"code": "choice", "message": f"{field} tidak valid"}]})
    return value


def _validate_uuid(field: str, value: str) -> str:
    try:
        return str(uuid_mod.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        raise ApiError.validation({field: [{"code": "invalid", "message": f"{field} harus UUID"}]}) from None


# ---------------------------------------------------------------------------
# Serialisasi (kontrak contracts.ts — ServiceRow/ServiceDetail/RadiusAccountRow)


def _first_account(service: Service) -> AccessAccount | None:
    accounts = list(service.access_accounts.all())
    return accounts[0] if accounts else None


def _isolation(account: AccessAccount | None) -> str:
    if account is None:
        return "normal"
    if account.state == AccessAccount.State.SUSPENDED:
        return "isolated"
    if account.state in (AccessAccount.State.DISABLED, AccessAccount.State.EXPIRED):
        return "hold"
    return "normal"


def service_row(service: Service, account: AccessAccount | None) -> dict:
    """ServiceRow — 4 dimensi terpisah (UI_UX §5), jangan digabung."""
    return {
        "id": str(service.id),
        "service_code": service.service_code,
        "customer_code": service.customer.customer_code,
        "customer_name": service.customer.display_name,
        "username": account.username if account else None,
        "kind": service.kind,
        "package_name": service.package_name or None,
        "router_id": str(service.router_id) if service.router_id else None,
        "router_display_name": service.router.display_name if service.router else None,
        "lifecycle": service.lifecycle,
        "payment": service.payment_status,
        "isolation": _isolation(account),
        # Beta: belum ada accounting/collector — unknown, bukan tebakan (§7).
        "connection": "unknown",
        # Beta: belum ada job perangkat per layanan — none (jujur).
        "job": "none",
        "incomplete_mapping": (not service.package_name) or (service.router_id is None),
    }


def service_detail(service: Service, account: AccessAccount | None) -> dict:
    data = service_row(service, account)
    customer = service.customer
    data.update(
        {
            "start_date": service.start_date.isoformat() if service.start_date else None,
            "contact": (customer.phone or customer.email) or None,
            "address": customer.address or None,
        }
    )
    if account is None:
        data["access"] = None
    else:
        data["access"] = {
            "username": account.username,
            "state": account.state,
            "credential_state": account.credential_state,
            "session_limit": account.simultaneous_use,
            "mac_locked": bool(account.mac_lock),
            "last_active_session_at": (
                account.last_active_session_at.isoformat() if account.last_active_session_at else None
            ),
            "restricting_router_id": str(service.router_id) if service.router_id else None,
        }
    return data


def radius_account_row(account: AccessAccount) -> dict:
    service = account.service
    return {
        "id": str(account.id),
        "username": account.username,
        "kind": account.kind,
        "state": account.state,
        "credential_state": account.credential_state,
        # Identitas layanan/pelanggan — diperlukan U10 (aktivasi massal TK-604):
        # daftar akun suspended harus dapat dihubungkan ke layanan + pelanggan
        # tanpa permintaan detail per baris.
        "service_id": str(service.id),
        "service_code": service.service_code,
        "customer_name": service.customer.display_name,
        "package_name": service.package_name or None,
        "restricting_router_id": str(service.router_id) if service.router_id else None,
        "last_active_session_at": (
            account.last_active_session_at.isoformat() if account.last_active_session_at else None
        ),
    }


def discovered_account_row(obj: DiscoveryObject) -> dict:
    return {
        "id": str(obj.id),
        "username": obj.username,
        "kind": obj.kind,
        "profile": obj.profile or None,
        "service": obj.router_service,
        "disabled_on_router": obj.disabled_on_router,
        "comment": obj.comment or None,
        "state": obj.state,
    }


def _paginate(request: Request, qs):
    """Paginasi kursor standar (created_at desc, id desc) — pola jobs view."""
    limit = parse_limit(request.query_params.get("limit"))
    cursor = request.query_params.get("cursor")
    if cursor:
        sort_key, last_id = decode_cursor(cursor)
        qs = qs.filter(created_at__lt=sort_key) | qs.filter(created_at=sort_key, id__lt=last_id)
    items = list(qs[: limit + 1])
    next_cursor = None
    if len(items) > limit:
        items = items[:limit]
        last = items[-1]
        next_cursor = encode_cursor(last.created_at.isoformat(), str(last.id))
    return items, next_cursor


# ---------------------------------------------------------------------------
# Services (U04)


class ServiceListView(TenantApiView):
    """GET /services (customers.read) + POST /services (services.provision).

    Izin per metode: GET daftar, POST provisioning akun (§5 Services row:
    izin provisioning hanya pada mutasi).
    """

    def get_permissions(self):
        self.required_permission = (
            "customers.read" if self.request.method in ("GET", "HEAD", "OPTIONS") else "services.provision"
        )
        return super().get_permissions()

    @extend_schema(summary="Daftar layanan tenant (kursor + dimensi tampilan)")
    def get(self, request: Request, tenant_id: str) -> Response:
        params = request.query_params
        qs = (
            Service.objects.filter(tenant_id=tenant_id)
            .select_related("customer", "router")
            .prefetch_related(
                Prefetch("access_accounts", queryset=AccessAccount.objects.order_by("created_at", "id"))
            )
        )
        kind = params.get("kind")
        if kind:
            qs = qs.filter(kind=_validate_choice("kind", kind, Service.Kind.values))
        lifecycle = params.get("lifecycle")
        if lifecycle:
            qs = qs.filter(lifecycle=_validate_choice("lifecycle", lifecycle, Service.Lifecycle.values))
        router_id = params.get("router_id")
        if router_id:
            qs = qs.filter(router_id=_validate_uuid("router_id", router_id))
        query = (params.get("query") or "").strip()
        if query:
            qs = qs.filter(
                Q(customer__display_name__icontains=query)
                | Q(service_code__icontains=query)
                | Q(access_accounts__username__icontains=query)
            ).distinct()
        payment = params.get("payment")
        if payment:
            qs = qs.filter(payment_status=_validate_choice("payment", payment, Service.PaymentStatus.values))
        # Dimensi isolation diturunkan dari state akun akses (§7).
        qs = qs.annotate(
            _susp=Exists(
                AccessAccount.objects.filter(service=OuterRef("pk"), state=AccessAccount.State.SUSPENDED)
            ),
            _hold=Exists(
                AccessAccount.objects.filter(
                    service=OuterRef("pk"), state__in=[AccessAccount.State.DISABLED, AccessAccount.State.EXPIRED]
                )
            ),
        )
        isolation = params.get("isolation")
        if isolation:
            _validate_choice("isolation", isolation, ("normal", "isolated", "awaiting_verification", "hold"))
            if isolation == "isolated":
                qs = qs.filter(_susp=True)
            elif isolation == "hold":
                qs = qs.filter(_hold=True)
            elif isolation == "normal":
                qs = qs.filter(_susp=False, _hold=False)
            else:  # awaiting_verification — belum ada pada beta (jujur: kosong).
                qs = Service.objects.none()
        connection = params.get("connection")
        if connection:
            _validate_choice("connection", connection, ("online", "offline", "unknown"))
            if connection != "unknown":
                # Belum ada accounting → online/offline tidak dapat diketahui.
                qs = Service.objects.none()
        job_dim = params.get("job")
        if job_dim:
            _validate_choice("job", job_dim, ("none", "queued", "running", "needs_review"))
            if job_dim != "none":
                qs = Service.objects.none()
        incomplete = params.get("incomplete_mapping")
        if incomplete is not None and incomplete != "":
            if incomplete in ("true", "1"):
                qs = qs.filter(Q(package_name="") | Q(router__isnull=True))
            elif incomplete in ("false", "0"):
                qs = qs.exclude(Q(package_name="") | Q(router__isnull=True))
            else:
                raise ApiError.validation(
                    {"incomplete_mapping": [{"code": "boolean", "message": "incomplete_mapping harus true/false"}]}
                )
        quick_tab = params.get("quick_tab")
        if quick_tab:
            _validate_choice("quick_tab", quick_tab, ("all", "unpaid", "paid_awaiting_activation", "isolated", "incomplete"))
            if quick_tab == "unpaid":
                qs = qs.filter(payment_status__in=[Service.PaymentStatus.UNBILLED, Service.PaymentStatus.PARTIAL])
            elif quick_tab == "paid_awaiting_activation":
                qs = Service.objects.none()  # beta: belum ada aktivasi tertunda
            elif quick_tab == "isolated":
                qs = qs.filter(_susp=True)
            elif quick_tab == "incomplete":
                qs = qs.filter(Q(package_name="") | Q(router__isnull=True))

        services_page, next_cursor = _paginate(request, qs.order_by("-created_at", "-id"))
        rows = [service_row(s, _first_account(s)) for s in services_page]
        return Response(page_response(rows, next_cursor))

    @idempotent("service_provision")
    @extend_schema(summary="Buat layanan: pelanggan + layanan draft + akun akses opsional")
    def post(self, request: Request, tenant_id: str) -> Response:
        service = services.provision_service_draft(request.mt_membership.tenant, _body(request), actor=request.user)
        return Response({"id": str(service.id), "state": service.lifecycle}, status=status.HTTP_201_CREATED)


class ServiceDetailView(TenantApiView):
    required_permission = "customers.read"

    @extend_schema(summary="Detail layanan + akun akses")
    def get(self, request: Request, tenant_id: str, service_id: str) -> Response:
        service = (
            Service.objects.filter(id=_validate_uuid("service_id", service_id), tenant_id=tenant_id)
            .select_related("customer", "router")
            .prefetch_related(
                Prefetch("access_accounts", queryset=AccessAccount.objects.order_by("created_at", "id"))
            )
            .first()
        )
        if service is None:
            raise ApiError.not_found()
        return Response(service_detail(service, _first_account(service)))


class RevealCredentialsView(TenantApiView):
    """Tampilkan password layanan — izin services.reveal_credentials (sensitif:
    reauth TOTP otomatis via TenantPermission) + no-store; respons tidak
    pernah di-cache idempotency (rahasia, §5/§7)."""

    required_permission = "services.reveal_credentials"

    @extend_schema(summary="Tampilkan kredensial layanan (sensitif — reauth)")
    def post(self, request: Request, tenant_id: str, service_id: str) -> Response:
        service = Service.objects.filter(id=_validate_uuid("service_id", service_id), tenant_id=tenant_id).first()
        if service is None:
            raise ApiError.not_found()
        account = service.access_accounts.order_by("created_at", "id").first()
        if account is None:
            raise ApiError.validation(
                {"username": [{"code": "required", "message": "Layanan ini belum memiliki akun akses"}]}
            )
        password = services.reveal_password(account)
        services._audit(
            tenant_id,
            "customers.credentials_revealed",
            actor=request.user,
            target_type="service",
            target_id=service.id,
            target_display=service.service_code,
        )
        return Response(
            {
                "username": account.username,
                "password": password,
                "display_for_s": 30,
                "revealed_at": timezone.now().isoformat(),
                "expires_in_s": 30,
            },
            headers={"Cache-Control": "no-store"},
        )


# ---------------------------------------------------------------------------
# Access accounts (U19)


class AccessAccountListView(TenantApiView):
    required_permission = "routers.read"

    @extend_schema(summary="Daftar akun akses RADIUS tenant")
    def get(self, request: Request, tenant_id: str) -> Response:
        params = request.query_params
        qs = AccessAccount.objects.filter(tenant_id=tenant_id).select_related(
            "service", "service__customer", "service__router"
        )
        query = (params.get("query") or "").strip()
        if query:
            qs = qs.filter(username__icontains=query)
        state = params.get("state")
        if state:
            qs = qs.filter(state=_validate_choice("state", state, AccessAccount.State.values))
        accounts, next_cursor = _paginate(request, qs.order_by("-created_at", "-id"))
        return Response(page_response([radius_account_row(a) for a in accounts], next_cursor))


class AccessAccountStateView(TenantApiView):
    required_permission = "services.activate"

    @idempotent("access_account_state", resource_from=lambda request, kwargs: str(kwargs.get("account_id", "")))
    @extend_schema(summary="Ubah state akun akses (suspended ↔ active)")
    def patch(self, request: Request, tenant_id: str, account_id: str) -> Response:
        account = AccessAccount.objects.filter(
            id=_validate_uuid("account_id", account_id), tenant_id=tenant_id
        ).select_related("service").first()
        if account is None:
            raise ApiError.not_found()
        new_state = str(_body(request).get("state", ""))
        services.set_account_state(account, new_state, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# CSV import (U08)


class CsvImportCreateView(TenantApiView):
    required_permission = "imports.run"

    @idempotent("csv_import_create")
    @extend_schema(summary="Unggah draf impor CSV (≤5000 baris)")
    def post(self, request: Request, tenant_id: str) -> Response:
        body = _body(request)
        mode = str(body.get("mode", ""))
        _validate_choice("mode", mode, CsvImport.Mode.values)
        file_name = str(body.get("file_name", "") or "").strip()[:255]
        if not file_name:
            raise ApiError.validation({"file_name": [{"code": "required", "message": "Nama berkas wajib diisi"}]})
        rows = body.get("rows")
        if not isinstance(rows, list):
            raise ApiError.validation({"rows": [{"code": "required", "message": "rows harus daftar baris"}]})
        if len(rows) > services.CSV_MAX_ROWS:
            raise ApiError.validation(
                {
                    "rows": [
                        {
                            "code": "max_rows",
                            "message": f"Maksimum {services.CSV_MAX_ROWS} baris",
                        }
                    ]
                }
            )
        csv_import = CsvImport.objects.create(
            tenant_id=tenant_id, mode=mode, file_name=file_name, rows=rows, created_by=request.user
        )
        # Bentuk CsvImportDraft kontrak (id) + import_id (spesifikasi M4).
        return Response(
            {
                "id": str(csv_import.id),
                "import_id": str(csv_import.id),
                "mode": csv_import.mode,
                "file_name": csv_import.file_name,
                "total_rows": len(rows),
                "validation": None,
            },
            status=status.HTTP_201_CREATED,
        )


class CsvImportValidateView(TenantApiView):
    required_permission = "imports.run"

    @idempotent("csv_import_validate", resource_from=lambda request, kwargs: str(kwargs.get("import_id", "")))
    @extend_schema(summary="Validasi draf impor CSV (sinkron)")
    def post(self, request: Request, tenant_id: str, import_id: str) -> Response:
        csv_import = CsvImport.objects.filter(id=_validate_uuid("import_id", import_id), tenant_id=tenant_id).first()
        if csv_import is None:
            raise ApiError.not_found()
        return Response(services.validate_csv(csv_import))


class CsvImportCommitView(TenantApiView):
    required_permission = "imports.run"

    @idempotent("csv_import_commit", resource_from=lambda request, kwargs: str(kwargs.get("import_id", "")))
    @extend_schema(summary="Commit draf impor CSV → job import_commit (202)")
    def post(self, request: Request, tenant_id: str, import_id: str) -> Response:
        csv_import = CsvImport.objects.filter(id=_validate_uuid("import_id", import_id), tenant_id=tenant_id).first()
        if csv_import is None:
            raise ApiError.not_found()
        if csv_import.state == CsvImport.State.COMMITTED:
            raise ApiError.conflict()
        # Cek mode dulu: fase belum tersedia → 503 jujur APA PUN state drafnya
        # (urutan penting: validasi mode beta memang selalu 503, state tak relevan).
        if csv_import.mode not in (CsvImport.Mode.CREATE, CsvImport.Mode.LINK):
            # update/device_mapping/password_migration — jujur 503 (§5).
            raise ApiError.unavailable()
        if csv_import.state != CsvImport.State.VALIDATED:
            # Paritas perilaku adapter mock: validasi belum dijalankan → 422.
            raise ApiError.validation(
                {"state": [{"code": "required", "message": "Validasi belum dijalankan"}]}
            )
        job = engine.create_job(
            tenant_id=tenant_id,
            kind="import_commit",
            actor=request.user,
            payload={"import_id": str(csv_import.id)},
        )
        return Response(
            {"job_id": str(job.id), "status_url": f"/api/v1/jobs/{job.id}"},
            status=status.HTTP_202_ACCEPTED,
        )


# ---------------------------------------------------------------------------
# Migration wizard (U07) — Tahap A DB-only (RADIUS.md §10.1)


class MigrationStartView(TenantApiView):
    required_permission = "migration.run"

    @idempotent("migration_start", resource_from=lambda request, kwargs: str(kwargs.get("router_id", "")))
    @extend_schema(summary="Mulai sesi migrasi router → job discover_router (202)")
    def post(self, request: Request, tenant_id: str, router_id: str) -> Response:
        router = Router.objects.filter(
            id=_validate_uuid("router_id", router_id), tenant_id=tenant_id, released_at=None
        ).first()
        if router is None:
            raise ApiError.not_found()
        session, job = services.start_migration(request.mt_membership.tenant, router, actor=request.user)
        return Response(
            {
                "migration_id": str(session.id),
                # job_id null bila handler discover_router (domain network,
                # dikerjakan paralel) belum terdaftar — jujur, tanpa job palsu.
                "job_id": str(job.id) if job else None,
                "status_url": f"/api/v1/jobs/{job.id}" if job else None,
                "state": session.state,
                "discovery_status": "queued" if job else "pending_handler",
            },
            status=status.HTTP_202_ACCEPTED,
        )


def _get_session(tenant_id: str, migration_id: str) -> MigrationSession:
    try:
        session = MigrationSession.objects.select_related("router", "snapshot").get(
            id=migration_id, tenant_id=tenant_id
        )
    except (MigrationSession.DoesNotExist, ValueError):
        raise ApiError.not_found() from None
    return session


class MigrationAccountsView(TenantApiView):
    required_permission = "customers.read"

    @extend_schema(summary="Daftar akun terdiscover sesi migrasi (kursor)")
    def get(self, request: Request, tenant_id: str, migration_id: str) -> Response:
        session = _get_session(tenant_id, _validate_uuid("migration_id", migration_id))
        limit = parse_limit(request.query_params.get("limit"))
        cursor = request.query_params.get("cursor")
        qs = (
            session.snapshot.discovery_objects.select_related("router").order_by("username", "id")
            if session.snapshot_id
            else DiscoveryObject.objects.none()
        )
        if cursor:
            sort_key, last_id = decode_cursor(cursor)
            qs = qs.filter(username__gt=sort_key) | qs.filter(username=sort_key, id__gt=last_id)
        items = list(qs[: limit + 1])
        next_cursor = None
        if len(items) > limit:
            items = items[:limit]
            last = items[-1]
            next_cursor = encode_cursor(last.username, str(last.id))
        return Response(page_response([discovered_account_row(o) for o in items], next_cursor))


class IdentityConflictsView(TenantApiView):
    required_permission = "customers.read"

    @extend_schema(summary="Kandidat konflik identitas lintas router tenant")
    def get(self, request: Request, tenant_id: str, migration_id: str) -> Response:
        session = _get_session(tenant_id, _validate_uuid("migration_id", migration_id))
        groups = services.identity_conflict_groups(tenant_id)
        decisions = {str(d.discovery_object_id): d for d in session.decisions.all()}
        candidates = []
        for group_id, group in groups.items():
            values = {
                decisions[str(obj.id)].decision
                for obj in group["objects"]
                if str(obj.id) in decisions
            }
            # Resolusi tampil hanya bila seluruh objek grup sepakat.
            resolution = None
            if len(values) == 1:
                value = next(iter(values))
                if value in ("merge", "keep_one", "rename"):
                    resolution = value
            candidates.append(
                {
                    "candidate_group_id": group_id,
                    "usernames": group["usernames"],
                    "routers": sorted(group["routers"].values()),
                    "kind": "structural_match",  # sebelum S1–S4: struktural saja (§10.1.1)
                    "resolution": resolution,
                }
            )
        return Response(candidates)


class IdentityConflictResolveView(TenantApiView):
    required_permission = "migration.run"

    @idempotent("identity_conflict_resolve", resource_from=lambda request, kwargs: str(kwargs.get("group_id", "")))
    @extend_schema(summary="Simpan resolusi konflik identitas (merge/keep_one/rename)")
    def post(self, request: Request, tenant_id: str, migration_id: str, group_id: str) -> Response:
        session = _get_session(tenant_id, _validate_uuid("migration_id", migration_id))
        body = _body(request)
        resolution = str(body.get("resolution", ""))
        new_username = str(body.get("new_username", "") or "")
        services.resolve_conflict_group(session, group_id, resolution, new_username)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MigrationCommitView(TenantApiView):
    required_permission = "migration.run"

    @idempotent("migration_commit", resource_from=lambda request, kwargs: str(kwargs.get("migration_id", "")))
    @extend_schema(summary="Commit adopsi migrasi → job commit_migration (202)")
    def post(self, request: Request, tenant_id: str, migration_id: str) -> Response:
        session = _get_session(tenant_id, _validate_uuid("migration_id", migration_id))
        if session.state == MigrationSession.State.COMMITTED:
            raise ApiError.conflict()
        if session.snapshot_id is None:
            raise ApiError.conflict()  # discovery belum selesai
        selected = _body(request).get("selected_account_ids")
        if selected is not None and not isinstance(selected, list):
            raise ApiError.validation(
                {"selected_account_ids": [{"code": "invalid", "message": "Harus daftar id objek discovery"}]}
            )
        # Ringkasan sinkron (MigrationSummaryCounts) disimpan ke session.counts
        # sebelum job dibuat; job commit_migration menghitung ulang nilai aktual
        # dan menimpa. Respons tetap ketat {job_id, status_url} (kontrak §5).
        session.counts = services.preview_migration_summary(
            session, [str(s) for s in selected] if selected else None
        )
        session.save(update_fields=["counts"])
        job = engine.create_job(
            tenant_id=tenant_id,
            kind="commit_migration",
            actor=request.user,
            router=session.router,
            payload={
                "session_id": str(session.id),
                "selected_account_ids": [str(s) for s in selected] if selected else None,
            },
        )
        return Response(
            {"job_id": str(job.id), "status_url": f"/api/v1/jobs/{job.id}"},
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordHarvestView(TenantApiView):
    required_permission = "migration.run"

    @idempotent("password_harvest", resource_from=lambda request, kwargs: str(kwargs.get("router_id", "")))
    @extend_schema(summary="Panen password router → job harvest_passwords (202, S1 lab)")
    def post(self, request: Request, tenant_id: str, router_id: str) -> Response:
        router = Router.objects.filter(
            id=_validate_uuid("router_id", router_id), tenant_id=tenant_id, released_at=None
        ).first()
        if router is None:
            raise ApiError.not_found()
        # 202 job; handler gagal jujur lab_required sampai S1 terverifikasi lab.
        job = engine.create_job(
            tenant_id=tenant_id,
            kind="harvest_passwords",
            actor=request.user,
            router=router,
            payload={"router_id": str(router.id)},
        )
        return Response(
            {"job_id": str(job.id), "status_url": f"/api/v1/jobs/{job.id}"},
            status=status.HTTP_202_ACCEPTED,
        )
