"""API registri router + enrollment (R1 fondasi + M3 core).

Endpoint M3: enrollment draft/issue, progress, bootstrap script (kanal
rahasasia Owner), probe (dipanggil router melalui tunnel; token di body),
discovery (job read-only). Cutover B0–B6 TIDAK dibangun pada beta —
release gate RADIUS belum lulus G1 (lihat docs/ACCEPTANCE.md §3).
"""
from __future__ import annotations

from django.utils import timezone as dj_timezone
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from adapters.routeros import simulator as routeros_simulator
from domains.common.envelope import ApiError
from domains.common.views import TenantApiView
from domains.jobs import engine as jobs_engine
from domains.network import enrollment as enrollment_service
from domains.network.models import Router, RouterEnrollment, RouterHealthSample

from .enrollment import EnrollmentError


class MachineTokenAuth:
    """Autentikasi kosong untuk endpoint MESIN (probe enrollment).

    Endpoint ini tidak memakai sesi/cookie — otorisasinya adalah token
    enrollment sekali pakai di body + verifikasi sumber tunnel (production).
    CSRF tidak relevan: tidak ada cookie autentikasi yang bisa dipakai
    serangan lintas situs; kelas ini HANYA untuk endpoint token-gated ini.
    """

    def authenticate(self, request):
        return None

    def authenticate_header(self, request):
        return None

# Adapter RouterOS aktif — simulator untuk dev/test; klien API-SSL nyata
# diaktifkan lewat MT_ROUTEROS_ADAPTER=api_ssl setelah bukti lab (G1).
def active_routeros_adapter():
    from django.conf import settings

    choice = getattr(settings, "MT_ROUTEROS_ADAPTER", "simulator")
    if choice == "simulator":
        return _SIM_ADAPTER
    from adapters.routeros.apiclient import ApiSslAdapter

    return ApiSslAdapter()


_SIM_ADAPTER = routeros_simulator.RouterOsSimulator()


def router_summary(router: Router, *, services_count: int = 0) -> dict:
    latest = router.health_samples.order_by("-observed_at").first()
    health = {
        "vpn": (None if latest is None or latest.vpn_up is None else ("up" if latest.vpn_up else "down")),
        "api": (None if latest is None or latest.api_up is None else ("up" if latest.api_up else "down")),
        "observed_at": latest.observed_at.isoformat() if latest else None,
    }
    # Tanpa sampel: unknown, bukan down (§11 — jangan membuat kesimpulan).
    if health["vpn"] is None:
        health["vpn"] = "unknown"
    if health["api"] is None:
        health["api"] = "unknown"
    return {
        "id": str(router.id),
        "display_name": router.display_name,
        "router_code": router.router_code,
        "location": router.location or None,
        "model": router.model or None,
        "routeros_version": router.routeros_version or None,
        "mode": router.mode,
        "health": health,
        "enforcement_mode": router.enforcement_mode,
        "services_count": services_count,
    }


class RouterListView(TenantApiView):
    required_permission = "routers.read"

    @extend_schema(summary="Daftar router tenant")
    def get(self, request: Request, tenant_id: str) -> Response:
        routers = Router.objects.filter(tenant_id=tenant_id, released_at=None).order_by("created_at")
        return Response([router_summary(r) for r in routers])


class RouterDetailView(TenantApiView):
    required_permission = "routers.read"

    @extend_schema(summary="Detail router")
    def get(self, request: Request, tenant_id: str, router_id: str) -> Response:
        router = Router.objects.filter(id=router_id, tenant_id=tenant_id, released_at=None).first()
        if router is None:
            raise ApiError.not_found()
        latest = router.health_samples.order_by("-observed_at").first()
        data = router_summary(router)
        data.update(
            {
                "identity": router.identity or None,
                "capability": router.capability or {},
                "uptime_s": latest.uptime_s if latest else None,
                "serial": router.serial or None,
                "tunnel_ip": router.tunnel_ip,
                "wireguard_pubkey": router.wireguard_pubkey or None,
            }
        )
        return Response(data)


class RouterEnrollmentCreateView(TenantApiView):
    """POST /tenants/{t}/router-enrollments — draft+issue; token SEKALI."""

    required_permission = "routers.enroll"

    @extend_schema(summary="Buat enrollment router (token ditampilkan sekali)")
    def post(self, request: Request, tenant_id: str) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            enrollment, token = enrollment_service.create_enrollment(
                tenant_id=tenant_id,
                actor=request.user,
                display_name=str(body.get("display_name", "")).strip(),
                router_code=str(body.get("router_code", "")).strip(),
                location=str(body.get("location", "")).strip(),
                model=str(body.get("model", "")).strip(),
            )
        except EnrollmentError as exc:
            raise ApiError(exc.code, f"enrollment.{exc.code}", status_code=exc.status, http_message=exc.message) from None
        return Response(
            {
                "id": str(enrollment.id),
                "request": {
                    "display_name": enrollment.display_name,
                    "router_code": enrollment.router_code,
                    "location": enrollment.location or None,
                    "model": enrollment.model or None,
                },
                "state": enrollment.state,
                "tunnel_ip": enrollment.tunnel_ip,
                "token": token,
                "token_expires_at": enrollment.token_expires_at.isoformat(),
                # Bootstrap tersedia lewat endpoint khusus (sekali per issue).
                "bootstrap_url": f"/api/v1/tenants/{tenant_id}/router-enrollments/{enrollment.id}/bootstrap",
            },
            status=201,
        )


def _enrollment_progress(enrollment: RouterEnrollment) -> dict:
    stages = [
        {"code": "draft", "state": "ok"},
        {"code": "enrollment_issued", "state": "ok" if enrollment.state != "draft" else "pending"},
        {
            "code": "bootstrap_pending",
            "state": "ok"
            if enrollment.state in ("bootstrap_pending", "tunnel_seen", "api_verified", "discovery_ready", "consumed")
            else "pending",
        },
        {
            "code": "tunnel_seen",
            "state": "ok" if enrollment.state in ("tunnel_seen", "api_verified", "discovery_ready", "consumed") else "pending",
        },
        {
            "code": "api_verified",
            "state": "ok" if enrollment.state in ("api_verified", "discovery_ready", "consumed") else "pending",
        },
        {
            "code": "discovery_ready",
            "state": "ok" if enrollment.state in ("discovery_ready", "consumed") else "pending",
        },
    ]
    state = enrollment.state
    if state in ("conflict", "expired"):
        for stage in stages:
            if stage["state"] == "pending":
                stage["state"] = "failed"
    if state == "consumed":
        # Consumed = router terdaftar; discovery_ready mengikuti snapshot.
        state = "api_verified"
    return {
        "enrollment_id": str(enrollment.id),
        "state": state,
        "stage_detail": stages,
        "router_id": str(enrollment.router_id) if enrollment.router_id else None,
        "tunnel_ip": enrollment.tunnel_ip,
        "expires_at": enrollment.expires_at.isoformat() if enrollment.expires_at else None,
    }


class RouterEnrollmentDetailView(TenantApiView):
    required_permission = "routers.read"

    @extend_schema(summary="Progress enrollment")
    def get(self, request: Request, tenant_id: str, enrollment_id: str) -> Response:
        enrollment = RouterEnrollment.objects.filter(id=enrollment_id, tenant_id=tenant_id).first()
        if enrollment is None:
            raise ApiError.not_found()
        return Response(_enrollment_progress(enrollment))


class RouterEnrollmentBootstrapView(TenantApiView):
    """GET bootstrap script — kanal rahasia (permission + reauth sensitif).

    Token enrollment diteruskan oleh UI (dari respons create). Script
    menyuntik password API CSPRNG platform; keduanya hanya lewat kanal ini.
    """

    required_permission = "routers.enroll"

    @extend_schema(summary="Skrip bootstrap enrollment (sensitif)")
    def get(self, request: Request, tenant_id: str, enrollment_id: str) -> Response:
        enrollment = RouterEnrollment.objects.filter(id=enrollment_id, tenant_id=tenant_id).first()
        if enrollment is None:
            raise ApiError.not_found()
        if enrollment.state not in (
            RouterEnrollment.State.ENROLLMENT_ISSUED,
            RouterEnrollment.State.BOOTSTRAP_PENDING,
        ):
            raise ApiError("enrollment_not_active", "enrollment.not_active", status_code=409)
        token = request.query_params.get("token", "")
        if not token:
            raise ApiError.validation(
                field_errors={"token": [{"code": "required", "message": "Token wajib disertakan (dari respons pembuatan)"}]}
            )
        from domains.common.crypto import hash_token

        if enrollment.token_hash != hash_token(token):
            raise ApiError("token_invalid", "enrollment.token_invalid", status_code=401, http_message="Token tidak cocok dengan enrollment")
        api_password = enrollment_service.generate_api_password()
        script = enrollment_service.generate_bootstrap_script(enrollment, token=token, api_password=api_password)
        enrollment_service.mark_bootstrap_downloaded(enrollment)
        # Password API disimpan terenkripsi (AEAD) pada enrollment; complete
        # memindahkannya ke router.credential_ref — tidak pernah plaintext
        # di DB maupun log/audit.
        from domains.common.crypto import SecretBox

        RouterEnrollment.objects.filter(id=enrollment.id).update(
            api_password_ref=SecretBox.encrypt(f"{enrollment.router_code}\x00{api_password}"),
            updated_at=dj_timezone.now(),
        )
        return Response(
            {
                "enrollment_id": str(enrollment.id),
                "script": script,
                "sensitive": True,
                "expires_at": enrollment.token_expires_at.isoformat() if enrollment.token_expires_at else None,
            }
        )


class RouterEnrollmentProbeView(TenantApiView):
    """POST /router-enrollments/{id}/probe — dipanggil ROUTER via tunnel.

    Bukan sesi pengguna: authentication_classes kosong; keamanan =
    token sekali pakai + TTL + nonce + (production) sumber IP tunnel.
    """

    required_permission = None
    authentication_classes: list = [MachineTokenAuth]
    permission_classes: list = []

    def initial(self, request, *args, **kwargs):
        # Melewati sesi; DRF permission default juga dilewati lewat
        # required_permission=None + custom dispatch kelas dasar hanya aktif
        # untuk route tenant — route ini TIDAK memakai TenantApiView.dispatch.
        from rest_framework.views import APIView

        APIView.initial(self, request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Jalur publik (token-gated); tidak membungkus tenant_scope.
        from rest_framework.views import APIView

        return APIView.dispatch(self, request, *args, **kwargs)

    @extend_schema(summary="Probe enrollment dari router (token di body)")
    def post(self, request: Request, enrollment_id: str) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        token = str(body.get("token", ""))
        nonce = str(body.get("nonce", ""))
        router_identity = str(body.get("router_identity", "")).strip()
        routeros_version = str(body.get("routeros_version", "")).strip()
        architecture = str(body.get("architecture", "")).strip()
        wireguard_pubkey = str(body.get("wireguard_pubkey", "")).strip()
        api_cert_fingerprint = str(body.get("api_cert_fingerprint", "")).strip()
        if not token or not nonce or not router_identity:
            raise ApiError.validation(
                field_errors={
                    "token": [{"code": "required", "message": "token wajib"}],
                    "nonce": [{"code": "required", "message": "nonce wajib"}],
                    "router_identity": [{"code": "required", "message": "router_identity wajib"}],
                }
            )
        source_ip = request.META.get("REMOTE_ADDR") or None
        try:
            enrollment, created = enrollment_service.complete_enrollment(
                enrollment_id=enrollment_id,
                token=token,
                nonce=nonce,
                router_identity=router_identity,
                routeros_version=routeros_version,
                architecture=architecture,
                wireguard_pubkey=wireguard_pubkey,
                api_cert_fingerprint=api_cert_fingerprint,
                source_ip=source_ip,
            )
        except EnrollmentError as exc:
            raise ApiError(exc.code, f"enrollment.{exc.code}", status_code=exc.status, http_message=exc.message) from None
        return Response(
            {
                "enrollment_id": str(enrollment.id),
                "state": "consumed" if created else "already_completed",
                "router_id": str(enrollment.router_id) if enrollment.router_id else None,
                "mode": "read_only",
                "next": "discovery",
            }
        )


class RouterDiscoveryView(TenantApiView):
    """POST discovery — job read-only (TK-401); tidak pernah menulis router."""

    required_permission = "routers.read"

    @extend_schema(summary="Mulai discovery read-only router")
    def post(self, request: Request, tenant_id: str, router_id: str) -> Response:
        router = Router.objects.filter(id=router_id, tenant_id=tenant_id, released_at=None).first()
        if router is None:
            raise ApiError.not_found()
        job = jobs_engine.create_job(
            tenant_id=tenant_id,
            kind="router_discovery",
            actor=request.user,
            router=router,
            payload={"router_id": str(router.id)},
            deadline_s=120,
        )
        return Response({"job_id": str(job.id), "status_url": f"/api/v1/jobs/{job.id}"}, status=202)


class RouterHealthProbeView(TenantApiView):
    """POST health probe — job sampling kesehatan (TK-303)."""

    required_permission = "routers.read"

    @extend_schema(summary="Mulai probe kesehatan router")
    def post(self, request: Request, tenant_id: str, router_id: str) -> Response:
        router = Router.objects.filter(id=router_id, tenant_id=tenant_id, released_at=None).first()
        if router is None:
            raise ApiError.not_found()
        job = jobs_engine.create_job(
            tenant_id=tenant_id,
            kind="router_health_probe",
            actor=request.user,
            router=router,
            payload={"router_id": str(router.id)},
            deadline_s=60,
        )
        return Response({"job_id": str(job.id), "status_url": f"/api/v1/jobs/{job.id}"}, status=202)
