"""API pelanggan/layanan — U04 (TK-405 subset beta) + reveal credentials.

POST /tenants/{t}/services membuat Customer+Service+AccessAccount+proyeksi
RADIUS dalam SATU transaksi (kuota layanan diperiksa atomik). Reveal
credential = services.reveal_credentials (sensitif: reauth) + audit.
Status pembayaran/isolir R2 tidak dipalsukan — connection_state hanya dari
accounting (default unknown).
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from domains.access import services as access_services
from domains.access.models import AccessAccount
from domains.access.services import AccessError
from domains.common.envelope import ApiError
from domains.common.idempotency import idempotent
from domains.common.pagination import decode_cursor, encode_cursor, parse_limit
from domains.common.views import TenantApiView
from domains.customers.models import Customer, Service
from domains.subscriptions import services as sub_services


def _service_row(service: Service, *, customer: Customer, account: AccessAccount | None) -> dict:
    return {
        "id": str(service.id),
        "customer_name": customer.full_name,
        "customer_id": str(customer.id),
        "display_name": service.display_name or customer.full_name,
        "state": service.state,
        "connection_state": service.connection_state,
        "payment": "not_billed",  # R2 belum aktif — jujur, bukan tebakan.
        "isolation": "normal",
        "router_id": str(service.router_id) if service.router_id else None,
        "package_code": service.package_code or None,
        "username": account.username if account else None,
        "access_account_id": str(account.id) if account else None,
        "created_at": service.created_at.isoformat(),
    }


class ServiceListView(TenantApiView):
    """GET daftar + POST buat layanan pada /tenants/{t}/services."""

    required_permission = "customers.read"

    def get_permissions(self):
        # POST memerlukan izin lebih tinggi — diverifikasi per-method.
        return super().get_permissions()

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method == "POST":
            from domains.common.views import resolve_membership
            from domains.tenancy.permissions import ROLE_PERMISSIONS

            # mt_membership belum tentu terpasang saat initial() — resolve langsung.
            membership = getattr(request, "mt_membership", None)
            if membership is None:
                membership = resolve_membership(request.user, kwargs.get("tenant_id") or "")
            allowed = "services.provision" in ROLE_PERMISSIONS.get(membership.role, frozenset()) if membership else False
            if not allowed:
                raise ApiError.forbidden("services.provision")

    @extend_schema(summary="Daftar layanan pelanggan")
    def get(self, request: Request, tenant_id: str) -> Response:
        limit = parse_limit(request.query_params.get("limit"))
        cursor = request.query_params.get("cursor")
        query = (request.query_params.get("query") or "").strip()
        connection = (request.query_params.get("connection") or "").strip()
        qs = (
            Service.objects.select_related("customer")
            .prefetch_related("access_accounts")
            .order_by("created_at", "id")
        )
        if query:
            from django.db.models import Q

            qs = qs.filter(
                Q(customer__full_name__icontains=query)
                | Q(display_name__icontains=query)
                | Q(access_accounts__username__icontains=query)
            ).distinct()
        if connection:
            if connection not in Service.Connection.values:
                raise ApiError.validation(
                    field_errors={"connection": [{"code": "invalid", "message": "Nilai connection tidak dikenal"}]}
                )
            qs = qs.filter(connection_state=connection)
        if cursor:
            sort_key, last_id = decode_cursor(cursor)
            qs = qs.filter(created_at__gt=sort_key) | qs.filter(created_at=sort_key, id__gt=last_id)
        rows = list(qs[: limit + 1])
        has_more = len(rows) > limit
        rows = rows[:limit]
        accounts = {a.service_id: a for a in AccessAccount.objects.filter(service_id__in=[s.id for s in rows])}
        next_cursor = None
        if has_more and rows:
            last = rows[-1]
            next_cursor = encode_cursor(last.created_at.isoformat(), str(last.id))
        return Response(
            {
                "items": [_service_row(s, customer=s.customer, account=accounts.get(s.id)) for s in rows],
                "next_cursor": next_cursor,
                "has_more": has_more,
            }
        )

    @extend_schema(summary="Buat layanan baru (pelanggan + akun akses)")
    @idempotent("create_service")
    def post(self, request: Request, tenant_id: str) -> Response:
        return ServiceCreateView().post(request, tenant_id)


class ServiceDetailView(TenantApiView):
    required_permission = "customers.read"

    @extend_schema(summary="Detail layanan")
    def get(self, request: Request, tenant_id: str, service_id: str) -> Response:
        service = (
            Service.objects.select_related("customer")
            .filter(id=service_id, tenant_id=tenant_id)
            .first()
        )
        if service is None:
            raise ApiError.not_found()
        account = service.access_accounts.order_by("created_at").first()
        data = _service_row(service, customer=service.customer, account=account)
        data.update(
            {
                "customer": {
                    "id": str(service.customer.id),
                    "full_name": service.customer.full_name,
                    "phone": service.customer.phone or None,
                    "email": service.customer.email or None,
                    "address": service.customer.address or None,
                },
                "simultaneous_use": account.simultaneous_use if account else None,
                "valid_until": account.valid_until.isoformat() if account and account.valid_until else None,
            }
        )
        return Response(data)


class ServiceCreateView:
    """POST /tenants/{t}/services — logika dipanggil dari ServiceListView.post."""

    def post(self, request: Request, tenant_id: str) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        customer_name = str(body.get("customer_name", "")).strip()
        username = str(body.get("username", "")).strip()
        password = str(body.get("password", ""))
        kind = str(body.get("kind", "pppoe")).strip()
        if not customer_name or len(customer_name) > 120:
            raise ApiError.validation(
                field_errors={"customer_name": [{"code": "required", "message": "Nama pelanggan wajib 1-120 karakter"}]}
            )
        if kind not in AccessAccount.Kind.values:
            raise ApiError.validation(
                field_errors={"kind": [{"code": "invalid", "message": "kind harus pppoe atau hotspot"}]}
            )
        router = None
        router_id = str(body.get("router_id", "") or "").strip()
        if router_id:
            from domains.network.models import Router

            router = Router.objects.filter(id=router_id, tenant_id=tenant_id, released_at=None).first()
            if router is None:
                raise ApiError.validation(
                    field_errors={"router_id": [{"code": "invalid", "message": "Router tidak ditemukan pada tenant"}]}
                )
        # Kuota layanan diperiksa atomik (reservasi dengan TTL; commit saat
        # seluruh pembuatan sukses; lepas bila ada yang gagal).
        reservation = sub_services.reserve(tenant_id, "services", 1)
        try:
            customer = Customer.objects.create(
                tenant_id=tenant_id,
                full_name=customer_name,
                phone=str(body.get("phone", "")).strip(),
                address=str(body.get("address", "")).strip(),
            )
            service = Service.objects.create(
                tenant_id=tenant_id,
                customer=customer,
                display_name=str(body.get("display_name", "")).strip(),
                state=Service.State.PROVISIONED,
                router=router,
                package_code=str(body.get("package_code", "")).strip(),
            )
            account = access_services.create_access_account(
                tenant_id=tenant_id,
                username=username,
                password=password,
                kind=kind,
                service=service,
                actor=request.user,
                router_id=str(router.id) if router else None,
                simultaneous_use=int(body.get("simultaneous_use", 1) or 1),
                rate_limit_rx_kbps=_int_or_none(body.get("rate_limit_rx_kbps")),
                rate_limit_tx_kbps=_int_or_none(body.get("rate_limit_tx_kbps")),
            )
            sub_services.commit_reservation(reservation)
        except AccessError as exc:
            sub_services.release_reservation(reservation)
            raise ApiError(exc.code, f"access.{exc.code}", status_code=400, http_message=exc.message) from None
        except Exception:
            sub_services.release_reservation(reservation)
            raise
        return Response({"id": str(service.id), "state": service.state, "access_account_id": str(account.id)}, status=201)


def _int_or_none(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ApiError.validation(
            field_errors={"rate_limit": [{"code": "integer", "message": "Kecepatan harus bilangan bulat (kbps)"}]}
        ) from None


class ServiceRevealCredentialsView(TenantApiView):
    """POST reveal — permission sensitif + reauth (PRD CUS-01; auto-hide UI 30 dtk)."""

    required_permission = "services.reveal_credentials"

    @extend_schema(summary="Tampilkan kredensial layanan (reauth + audit)")
    @idempotent("reveal_credentials")
    def post(self, request: Request, tenant_id: str, service_id: str) -> Response:
        service = Service.objects.filter(id=service_id, tenant_id=tenant_id).first()
        if service is None:
            raise ApiError.not_found()
        account = service.access_accounts.order_by("created_at").first()
        if account is None:
            raise ApiError("no_access_account", "access.no_access_account", status_code=404, http_message="Layanan tidak memiliki akun akses")
        try:
            password = access_services.reveal_password(account)
        except AccessError as exc:
            raise ApiError(exc.code, f"access.{exc.code}", status_code=404, http_message=exc.message) from None
        from domains.audit.models import record

        record(
            tenant_id=tenant_id,
            action_code="services.credentials_revealed",
            actor_display=getattr(request.user, "full_name", "") or getattr(request.user, "email", ""),
            actor_id=getattr(request.user, "id", None),
            target_type="service",
            target_id=str(service.id),
            target_display=account.username,
            payload={"username": account.username},
        )
        return Response(
            {
                "username": account.username,
                "password": password,
                "valid_until": account.valid_until.isoformat() if account.valid_until else None,
                "auto_hide_seconds": 30,
            }
        )


class CsvImportCreateView(TenantApiView):
    """POST /tenants/{t}/imports — unggah baris CSV (S2; batas 10k/10MiB)."""

    required_permission = "imports.run"

    @extend_schema(summary="Buat impor CSV")
    def post(self, request: Request, tenant_id: str) -> Response:
        from domains.customers import csv_import as csv_service

        body = request.data if isinstance(request.data, dict) else {}
        rows = body.get("rows")
        if not isinstance(rows, list):
            raise ApiError.validation(
                field_errors={"rows": [{"code": "required", "message": "rows wajib berupa daftar baris"}]}
            )
        try:
            csv = csv_service.create_import(
                tenant_id=tenant_id,
                actor=request.user,
                mode=str(body.get("mode", "create")),
                file_name=str(body.get("file_name", "")).strip(),
                rows=[r if isinstance(r, dict) else {} for r in rows],
            )
        except csv_service.CsvImportError as exc:
            raise ApiError(exc.code, f"csv.{exc.code}", status_code=400, http_message=exc.message) from None
        return Response(
            {
                "id": str(csv.id),
                "mode": csv.mode,
                "file_name": csv.file_name,
                "total_rows": len(csv.rows),
                "validation": None,
                "state": csv.state,
            },
            status=201,
        )


class CsvImportValidateView(TenantApiView):
    required_permission = "imports.run"

    @extend_schema(summary="Validasi impor CSV (tanpa menulis)")
    def post(self, request: Request, tenant_id: str, import_id: str) -> Response:
        from domains.customers import csv_import as csv_service
        from domains.customers.models import CsvImport

        csv = CsvImport.objects.filter(id=import_id, tenant_id=tenant_id).first()
        if csv is None:
            raise ApiError.not_found()
        validation = csv_service.run_validation(csv)
        return Response(validation)


class CsvImportCommitView(TenantApiView):
    """POST commit → job csv_import_commit (idempoten per baris)."""

    required_permission = "imports.run"

    @extend_schema(summary="Jalankan impor CSV (job)")
    def post(self, request: Request, tenant_id: str, import_id: str) -> Response:
        from domains.customers.models import CsvImport
        from domains.jobs import engine as jobs_engine

        csv = CsvImport.objects.filter(id=import_id, tenant_id=tenant_id).first()
        if csv is None:
            raise ApiError.not_found()
        if csv.state not in (CsvImport.State.UPLOADED, CsvImport.State.VALIDATED):
            raise ApiError("import_not_commitable", "csv.import_not_commitable", status_code=409)
        job = jobs_engine.create_job(
            tenant_id=tenant_id,
            kind="csv_import_commit",
            actor=request.user,
            payload={"import_id": str(csv.id)},
            deadline_s=600,
        )
        return Response({"job_id": str(job.id), "status_url": f"/api/v1/jobs/{job.id}"}, status=202)
