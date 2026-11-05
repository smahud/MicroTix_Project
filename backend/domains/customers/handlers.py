"""Handler job domain pelanggan: commit impor CSV (S2)."""
from __future__ import annotations

from typing import Any

from domains.jobs.engine import JobContext, JobError, JobHandler, register


class CsvImportCommitHandler(JobHandler):
    kind = "csv_import_commit"

    def preflight(self, ctx: JobContext) -> None:
        from domains.customers.models import CsvImport

        csv = CsvImport.objects.filter(id=ctx.payload.get("import_id")).first()
        if csv is None:
            raise JobError(code="import_not_found", retryable=False)

    def execute(self, ctx: JobContext) -> dict[str, Any]:
        from domains.customers import csv_import as csv_service
        from domains.customers.models import CsvImport

        csv = CsvImport.objects.filter(id=ctx.payload.get("import_id")).first()
        assert csv is not None
        result = csv_service.commit_rows(csv, actor=None)
        ctx.progress(total=result["created"] + result["skipped"] + result["failed"], done=result["created"] + result["skipped"] + result["failed"])
        return result

    def verify(self, ctx: JobContext) -> dict[str, Any] | None:
        from domains.customers.models import CsvImport

        csv = CsvImport.objects.filter(id=ctx.payload.get("import_id")).first()
        if csv is None or csv.state != CsvImport.State.COMMITTED:
            raise JobError(code="import_not_committed", retryable=True)
        # Readback lulus — hasil execute (created/skipped/failed) dipertahankan.
        return None


def register_handlers() -> None:
    from domains.jobs.engine import handler_for

    if handler_for(CsvImportCommitHandler.kind) is None:
        register(CsvImportCommitHandler())
