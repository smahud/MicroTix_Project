"""Handler job domain customers — import_commit, commit_migration, harvest_passwords.

Didaftarkan di CustomersConfig.ready(). Semua handler berjalan dalam
tenant_scope job (dibungkus engine.run_claimed) dan hanya menulis DB
(Tahap A) — tidak pernah menyentuh router.
"""
from __future__ import annotations

from domains.common.envelope import ApiError
from domains.customers import services
from domains.customers.models import CsvImport, MigrationSession
from domains.jobs.engine import JobContext, JobError, JobHandler


def _to_job_error(exc: ApiError) -> JobError:
    """Konversi ApiError layanan → JobError (kode mesin stabil; §5/§6).

    quota/conflict/not_found/validation tidak diulang otomatis;
    dependency_unavailable retryable (ketergantungan mungkin pulih).
    """
    return JobError(
        code=exc.code,
        retryable=exc.code == "dependency_unavailable",
        message=str(exc.detail),
    )


class ImportCommitHandler(JobHandler):
    """import_commit: commit draf CSV tervalidasi (mode create/link)."""

    kind = "import_commit"

    def preflight(self, ctx: JobContext) -> None:
        import_id = str(ctx.payload.get("import_id", ""))
        csv_import = CsvImport.objects.filter(id=import_id).first()
        if csv_import is None:
            raise JobError(code="not_found", retryable=False, message="Draf impor tidak ditemukan")

    def execute(self, ctx: JobContext) -> dict:
        import_id = str(ctx.payload.get("import_id", ""))
        csv_import = CsvImport.objects.select_related("tenant").get(id=import_id)
        total = int((csv_import.validation or {}).get("valid_rows") or 0)
        ctx.progress(phase="committing", done=0, total=total or None)
        try:
            summary = services.commit_csv(csv_import)
        except ApiError as exc:
            raise _to_job_error(exc) from None
        created = int(summary.get("created", summary.get("linked", 0)) or 0)
        ctx.progress(phase="committing", done=created or total, total=total or None)
        return {"summary": summary}

    def verify(self, ctx: JobContext) -> dict:
        import_id = str(ctx.payload.get("import_id", ""))
        csv_import = CsvImport.objects.get(id=import_id)
        if csv_import.state != CsvImport.State.COMMITTED:
            raise JobError(code="verification_failed", retryable=False, message="Draf tidak berstatus committed")
        return {"state": csv_import.state, "summary": (csv_import.validation or {}).get("commit_summary", {})}


class CommitMigrationHandler(JobHandler):
    """commit_migration: adopsi DB-only objek discovery (RADIUS.md §10.1.5)."""

    kind = "commit_migration"

    def preflight(self, ctx: JobContext) -> None:
        session_id = str(ctx.payload.get("session_id", ""))
        session = MigrationSession.objects.filter(id=session_id).first()
        if session is None:
            raise JobError(code="not_found", retryable=False, message="Sesi migrasi tidak ditemukan")

    def execute(self, ctx: JobContext) -> dict:
        session_id = str(ctx.payload.get("session_id", ""))
        session = MigrationSession.objects.select_related("router", "snapshot").get(id=session_id)
        selected = ctx.payload.get("selected_account_ids")
        ctx.progress(phase="adopting", done=0, total=None)
        try:
            counts = services.commit_migration(session, selected_ids=selected)
        except ApiError as exc:
            raise _to_job_error(exc) from None
        ctx.progress(phase="adopting", done=counts.get("to_create", 0), total=counts.get("to_create", 0) or None)
        return {"counts": counts}

    def verify(self, ctx: JobContext) -> dict:
        session_id = str(ctx.payload.get("session_id", ""))
        session = MigrationSession.objects.get(id=session_id)
        if session.state != MigrationSession.State.COMMITTED:
            raise JobError(code="verification_failed", retryable=False, message="Sesi tidak berstatus committed")
        # Readback: objek adopted tidak menyisakan DeviceOperation applying
        # (commit Tahap A tidak menyentuh router — diverifikasi di tes).
        return {"state": session.state, "counts": session.counts}


class HarvestPasswordsHandler(JobHandler):
    """harvest_passwords (S1) — panen password dari router.

    S1 (RADIUS.md §10.1.2, ROUTEROS.md §3) memerlukan akun sementara
    privileged `rtrw-mig` pada router NYATA, persetujuan Owner, dan verifikasi
    lab (policy `sensitive` hanya bila dibuktikan lab). Adapter simulator
    TIDAK menyediakan pembacaan password (list_accounts selalu menghapus
    field password) dan registri adapter belum tersedia. Beta: gagal JUJUR
    dengan kode lab_required — tidak ada sukses/panen palsu.
    """

    kind = "harvest_passwords"

    def preflight(self, ctx: JobContext) -> None:
        raise JobError(
            code="lab_required",
            retryable=False,
            recovery_required=False,
            message=(
                "Panen password (S1) memerlukan akun sementara privileged pada router nyata "
                "dan verifikasi lab sesuai ROUTEROS.md §3; belum tersedia pada beta."
            ),
        )

    def execute(self, ctx: JobContext) -> dict:  # pragma: no cover — preflight selalu gagal
        raise JobError(code="lab_required", retryable=False, message="S1 memerlukan lab (ROUTEROS.md §3)")

    def verify(self, ctx: JobContext) -> dict:  # pragma: no cover
        return {}


HANDLERS: tuple[JobHandler, ...] = (ImportCommitHandler(), CommitMigrationHandler(), HarvestPasswordsHandler())
