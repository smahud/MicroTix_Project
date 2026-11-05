"""Impor CSV (S2) — validasi + commit idempoten (TK-404 subset beta).

Validasi: kolom username/password wajib; username mengikuti aturan RAD-02
(case-sensitive, ≤64 karakter, tanpa kontrol/spasi tepi); password ≥8.
Commit: baris dengan username yang sudah ada DILEWATI dan dilaporkan
(idempoten), bukan ditimpa; hasil per baris dikembalikan pada job result.
"""
from __future__ import annotations

from django.utils import timezone as dj_timezone

from domains.access import services as access_services
from domains.access.services import AccessError, validate_username
from domains.customers.models import CsvImport

MAX_ROWS = 10_000
MAX_BYTES = 10 * 1024 * 1024


class CsvImportError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        self.message = message or code
        super().__init__(self.message)


def validate_rows(rows: list[dict]) -> dict:
    """Validasi seluruh baris; hasil per baris + ringkasan (tanpa menulis)."""
    issues: list[dict] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=2):  # baris 1 = header
        username = str(row.get("username", "") or "").strip()
        password = str(row.get("password", "") or "")
        row_issues: list[str] = []
        try:
            validate_username(username)
        except ValueError as exc:
            row_issues.append(f"username: {exc}")
        if username in seen:
            row_issues.append("username: duplikat dalam berkas")
        seen.add(username)
        if len(password) < 8:
            row_issues.append("password: minimal 8 karakter")
        kind = str(row.get("kind", "pppoe") or "pppoe").strip()
        if kind not in ("pppoe", "hotspot"):
            row_issues.append("kind: harus pppoe atau hotspot")
        if row_issues:
            issues.append({"row": index, "username": username, "issues": row_issues})
    return {
        "total_rows": len(rows),
        "valid_rows": len(rows) - len(issues),
        "invalid_rows": len(issues),
        "issues": issues[:200],  # batasi ukuran respons; sisanya diringkas
        "issues_truncated": len(issues) > 200,
    }


def create_import(*, tenant_id, actor, mode: str, file_name: str, rows: list[dict]) -> CsvImport:
    if mode not in CsvImport.Mode.values:
        raise CsvImportError("invalid_mode", "mode harus create atau update")
    if not file_name or len(file_name) > 200:
        raise CsvImportError("invalid_file_name", "Nama berkas wajib 1-200 karakter")
    if len(rows) > MAX_ROWS:
        raise CsvImportError("too_many_rows", f"Maksimum {MAX_ROWS} baris per impor")
    payload_bytes = sum(len(str(r).encode("utf-8")) for r in rows)
    if payload_bytes > MAX_BYTES:
        raise CsvImportError("too_large", "Ukuran data melebihi 10 MiB")
    return CsvImport.objects.create(
        tenant_id=tenant_id,
        created_by=actor,
        mode=mode,
        file_name=file_name,
        rows=rows,
        state=CsvImport.State.UPLOADED,
    )


def run_validation(csv_import: CsvImport) -> dict:
    validation = validate_rows(csv_import.rows)
    csv_import.validation = validation
    csv_import.state = CsvImport.State.VALIDATED
    csv_import.updated_at = dj_timezone.now()
    csv_import.save(update_fields=["validation", "state", "updated_at"])
    return validation


def commit_rows(csv_import: CsvImport, *, actor=None) -> dict:
    """Commit idempoten: username existing dilewati; hasil per baris.

    Dipanggil oleh job csv_import_commit dalam tenant_scope.
    """
    created, skipped, failed = 0, 0, 0
    failures: list[dict] = []
    for row in csv_import.rows:
        username = str(row.get("username", "") or "").strip()
        password = str(row.get("password", "") or "")
        kind = str(row.get("kind", "pppoe") or "pppoe").strip() or "pppoe"
        try:
            access_services.create_access_account(
                tenant_id=csv_import.tenant_id,
                username=username,
                password=password,
                kind=kind,
                actor=actor,
            )
            created += 1
        except AccessError as exc:
            if exc.code == "username_taken":
                skipped += 1
            else:
                failed += 1
                failures.append({"username": username, "code": exc.code})
        except ValueError as exc:
            failed += 1
            failures.append({"username": username, "code": "invalid_username", "message": str(exc)})
    csv_import.state = CsvImport.State.COMMITTED
    csv_import.updated_at = dj_timezone.now()
    csv_import.save(update_fields=["state", "updated_at"])
    return {"created": created, "skipped": skipped, "failed": failed, "failures": failures[:50]}
