"""API backup router — U12 (M5).

GET  /tenants/{t}/backups?router_id=   → [BackupArtifact] (backups.run)
GET  /tenants/{t}/backup-schedules     → [BackupSchedule] (backups.run)
POST /tenants/{t}/routers/{r}/backups  → 202 JobAccepted kind backup_run
     (backups.run; Idempotency-Key wajib — §5).
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from domains.backups import service
from domains.backups.models import BackupArtifact, BackupSchedule
from domains.backups.service import API_CATEGORY
from domains.common.envelope import ApiError
from domains.common.idempotency import idempotent
from domains.common.views import TenantApiView
from domains.config.registry import registry
from domains.jobs import engine
from domains.network.models import Router

# Pemetaan state katalog → transfer_state kontrak (contracts.ts BackupArtifact):
# generating → staging (pipeline bertahap §5); committed/failed langsung.
API_TRANSFER_STATE = {
    BackupArtifact.State.GENERATING: "staging",
    BackupArtifact.State.COMMITTED: "committed",
    BackupArtifact.State.FAILED: "failed",
}


def artifact_info(artifact: BackupArtifact) -> dict:
    """Bentuk BackupArtifact kontrak frontend (contracts.ts)."""
    return {
        "id": str(artifact.id),
        "router_id": str(artifact.router_id),
        "generation": artifact.generation,
        "created_at": artifact.created_at.isoformat(),
        "category": API_CATEGORY.get(artifact.category, artifact.category),
        "size_bytes": artifact.size_bytes if artifact.size_bytes is not None else 0,
        "transfer_state": API_TRANSFER_STATE.get(artifact.state, "failed"),
        # Binary terenkripsi password per router CSPRNG (§5) — status enkripsi
        # selalu true untuk artifact platform.
        "encrypted": True,
    }


def schedule_info(schedule: BackupSchedule, timezone_name: str) -> dict:
    """Bentuk BackupSchedule kontrak frontend (contracts.ts)."""
    return {
        "router_id": str(schedule.router_id),
        "timezone": timezone_name,
        "frequency": "daily" if schedule.routine_interval_hours <= 24 else "weekly",
        "time_local": schedule.routine_time_local.strftime("%H:%M"),
        "artifact_type": "binary",
        # OPS-05: notifikasi default off sampai dikonfigurasi tenant.
        "notification_enabled": False,
        # Bidang tambahan (kebijakan retensi §5) — kontrak membolehkan ekstra.
        "retention": schedule.retention,
        "manual_retention": schedule.manual_retention,
        "prechange_retention": schedule.prechange_retention,
        "enabled": schedule.enabled,
    }


def ensure_schedule(tenant_id: str, router: Router) -> BackupSchedule:
    """Jadwal default per router (lazy) — retensi defaults.json backup.*_max."""
    schedule, _ = BackupSchedule.objects.get_or_create(
        tenant_id=tenant_id,
        router=router,
        defaults={
            "routine_interval_hours": 24,
            "retention": registry().get_int("backup.routine_max"),
            "manual_retention": registry().get_int("backup.manual_max"),
            "prechange_retention": registry().get_int("backup.prechange_max"),
            "enabled": True,
        },
    )
    return schedule


class BackupArtifactListView(TenantApiView):
    required_permission = "backups.run"

    @extend_schema(summary="Daftar artifact backup tenant (retained membership)")
    def get(self, request: Request, tenant_id: str) -> Response:
        qs = BackupArtifact.objects.exclude(state=BackupArtifact.State.PRUNED).order_by("-generation", "-created_at")
        router_id = request.query_params.get("router_id")
        if router_id:
            qs = qs.filter(router_id=router_id)
        return Response([artifact_info(a) for a in qs])


class BackupScheduleListView(TenantApiView):
    required_permission = "backups.run"

    @extend_schema(summary="Jadwal backup per router beserta kebijakan retensi")
    def get(self, request: Request, tenant_id: str) -> Response:
        from domains.tenancy.models import Tenant

        tenant = Tenant.objects.filter(id=tenant_id).first()
        tz_name = tenant.timezone if tenant else "Asia/Jakarta"
        schedules = []
        for router in Router.objects.filter(tenant_id=tenant_id, released_at=None).order_by("created_at"):
            schedules.append(schedule_info(ensure_schedule(tenant_id, router), tz_name))
        return Response(schedules)


class RunBackupView(TenantApiView):
    required_permission = "backups.run"

    @idempotent("backup_run", resource_from=lambda request, kwargs: kwargs.get("router_id", ""))
    @extend_schema(summary="Jalankan backup sekarang → job backup_run")
    def post(self, request: Request, tenant_id: str, router_id: str) -> Response:
        router = Router.objects.filter(id=router_id, tenant_id=tenant_id, released_at=None).first()
        if router is None:
            raise ApiError.not_found()
        body = request.data if isinstance(request.data, dict) else {}
        # Tombol "backup sekarang" = operator memicu → kategori manual (§5);
        # kategori lain dapat diberikan eksplisit oleh pemanggil terpelajar.
        category = str(body.get("category") or BackupArtifact.Category.MANUAL)
        if category not in API_CATEGORY:
            raise ApiError.validation(
                {"category": [{"code": "choice", "message": "category harus routine/manual/prechange"}]}
            )
        job = engine.create_job(
            tenant_id=tenant_id,
            kind=service.BACKUP_RUN_KIND,
            actor=request.user,
            actor_display=getattr(request.user, "full_name", "") or getattr(request.user, "email", ""),
            router=router,
            payload={"category": category, "router_id": str(router.id)},
            request_id=getattr(request, "mt_request_id", None),
            deadline_s=registry().get_int("backup.job_deadline_s"),
        )
        return Response(
            {"job_id": str(job.id), "status_url": f"/api/v1/jobs/{job.id}"},
            status=status.HTTP_202_ACCEPTED,
        )
