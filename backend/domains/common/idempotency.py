"""Idempotency-Key untuk mutasi (ARCHITECTURE.md §5).

Scope: principal + tenant/platform + operation + resource + key.
Body dibandingkan HMAC; sama+isi sama → replay respons logis; isi berbeda →
409 idempotency_conflict. Retensi 7 hari.

Protokol claim/replay (PA-006) — satu transaksi PostgreSQL:
1. Klaim `INSERT ... ON CONFLICT DO NOTHING RETURNING` pada identitas
   canonical; concurrent same-key menunggu konflik unik (bukan 500).
2. Klaiman kalah: body beda → 409 idempotency_conflict tanpa efek kedua;
   body sama + respons tersimpan → replay; body sama + respons belum ada →
   klaim ambigu → tolak aman, tidak eksekusi ulang buta.
3. Klaiman menang: view dieksekusi; respons 2xx disimpan DALAM transaksi
   yang sama dengan efek domain (commit atomik: "crash setelah commit domain
   sebelum respons tersimpan" tidak lagi bisa terjadi pada jalur ini).
   Exception apa pun → rollback klaim + efek; retry memakai key semula.

Identitas canonical: UUID (tenant/resource) dinormalkan ke bentuk lowercase
standar — semua ejaan alias (huruf besar/urn/kurung/tanpa hyphen) menjadi
scope yang sama; input salah bentuk → 422. String semantik (username, pesan,
body) TIDAK diubah. Operasi platform memakai scope eksplisit `platform`
yang tidak bergeser ketika operator berpindah active tenant.
"""
from __future__ import annotations

import functools
import hashlib
import hmac
import json
import uuid as _uuid
from typing import Any, Callable

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response

from domains.common.envelope import ApiError
from domains.jobs.models import IdempotencyKey

TTL_S = 7 * 24 * 3600
PLATFORM_SCOPE = "platform"
_CLAIM_ATTEMPTS = 3


def _body_hash(body: Any) -> str:
    canonical = json.dumps(body or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hmac.new(settings.SECRET_KEY.encode(), canonical.encode(), hashlib.sha256).hexdigest()


def _principal(request) -> str:
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return str(user.id)
    return "anonymous"


def _canonical_uuid(value: Any, field: str, *, allow_empty: bool = False) -> str:
    """Normalisasi ejaan alias UUID → canonical lowercase; salah bentuk → 422."""
    raw = str(value or "").strip()
    if not raw:
        if allow_empty:
            return ""
        raise ApiError.validation(
            {field: [{"code": "required", "message": f"{field} wajib"}]}
        )
    try:
        return str(_uuid.UUID(raw))
    except (ValueError, AttributeError, TypeError):
        raise ApiError.validation(
            {field: [{"code": "invalid", "message": f"{field} bukan UUID valid"}]}
        ) from None


def _claim_id(
    principal: str, tenant_part: str, operation: str, resource: str, key: str, body_h: str
) -> tuple[int | None, IdempotencyKey | None]:
    """Klaim record idempotency conflict-safe; kembalikan (claimed_id, record).

    INSERT ... ON CONFLICT DO NOTHING memaksa konkuren same-identity menunggu
    keputusan transaksi klaiman pertama (PostgreSQL speculative insert), lalu
    `RETURNING id` membedakan pemilik klaim dari yang kalah. Loop singkat
    menutup race kecil: record kedaluwarsa terhapus konkuren antara INSERT
    dan SELECT ulang. Klaiman kalah menerima record existing terbaca segar
    setelah transaksi pemilik klaim ter-commit.
    """
    from django.db import connection

    for _ in range(_CLAIM_ATTEMPTS):
        with connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO jobs_idempotency_key
                    (principal, tenant_scope, operation, resource, idem_key, body_hash, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT ON CONSTRAINT uq_idem_identity DO NOTHING
                RETURNING id
                """,
                [principal, tenant_part, operation, resource, key, body_h, timezone.now()],
            )
            row = cur.fetchone()
        if row is not None:
            return row[0], None
        existing = IdempotencyKey.objects.filter(
            principal=principal,
            tenant_scope=tenant_part,
            operation=operation,
            resource=resource,
            idem_key=key,
        ).first()
        if existing is not None:
            return None, existing
    # Race berulang (cleanup TTL konkuren) — kondisi aneh, bukan 500: tolak
    # aman dan biarkan klien mencoba ulang (retryable bukan duplikat efek).
    raise ApiError.conflict("idempotency_conflict", "error.idempotency_conflict")


def idempotent(
    operation: str,
    resource_from: Callable[[Any, Any], str] | None = None,
    *,
    platform: bool = False,
    resource_uuid: bool = True,
):
    """Dekorator view DRF: claim/replay respons per Idempotency-Key.

    `platform=True` → scope eksplisit `platform` (operasi lintas tenant:
    keputusan antrean pembayaran SaaS); tidak pernah diambil dari sesi
    active tenant sehingga operator berpindah tenant tidak membuat scope
    baru. Tanpa flag: tenant dari URL (kanonikalisasi UUID), fallback sesi
    active tenant — kompatibel view resource-scoped.
    `resource_uuid=False` → resource adalah token opaque exact-case
    (mis. sha256[:16] grup konflik identitas) — tidak di-kanonikalisasi;
    validasi bentuk tetap milik domain/view.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, request: Any, *args: Any, **kwargs: Any):
            key = request.headers.get("Idempotency-Key", "").strip()
            if not key:
                # Wajib untuk uang/provisioning/commit/cutover/backup/aktivasi.
                raise ApiError.validation(
                    {"idempotency_key": [{"code": "required", "message": "Idempotency-Key wajib"}]}
                )
            if len(key) > 128:
                raise ApiError.validation(
                    {"idempotency_key": [{"code": "max_length", "message": "Idempotency-Key terlalu panjang"}]}
                )

            principal = _principal(request)
            if platform:
                tenant_part = PLATFORM_SCOPE
            else:
                tenant_raw = kwargs.get("tenant_id") or request.session.get("active_tenant_id") or ""
                if tenant_raw:
                    tenant_part = _canonical_uuid(tenant_raw, "tenant_id")
                else:
                    tenant_part = PLATFORM_SCOPE
            resource_raw = resource_from(request, kwargs) if resource_from else kwargs.get("resource_id", "")
            if resource_uuid:
                resource = _canonical_uuid(resource_raw, "resource_id", allow_empty=True)
            else:
                resource = str(resource_raw or "").strip()
            body_h = _body_hash(getattr(request, "data", None))

            with transaction.atomic():
                # Retensi 7 hari: kelas data cache; business uniqueness
                # domain tetap menjaga duplikasi setelah record terhapus.
                cutoff = timezone.now() - timezone.timedelta(seconds=TTL_S)
                IdempotencyKey.objects.filter(created_at__lt=cutoff).delete()

                claimed_id, existing = _claim_id(
                    principal, tenant_part, operation, resource, key, body_h
                )
                if claimed_id is None:
                    if existing.body_hash != body_h:
                        raise ApiError.conflict("idempotency_conflict", "error.idempotency_conflict")
                    if existing.response_status is None:
                        # Record terkomit tanpa respons = klaim protokol lama
                        # (pra-migrasi 0004) yang efeknya tak bisa dibuktikan
                        # — tolak aman, jangan eksekusi ulang buta. Migrasi
                        # menghapus record seperti ini; cabang ini defensif.
                        raise ApiError.conflict(
                            "idempotency_conflict", "error.idempotency_conflict"
                        )
                    # Replay respons logis: satu aksi logis, hasil sama.
                    return Response(existing.response_body, status=existing.response_status)

                response = func(self, request, *args, **kwargs)
                # Respons 2xx disimpan dalam transaksi protokol yang sama
                # dengan efek domain → commit atomik. Respons galat tidak
                # disimpan (exception → rollback klaim; retry memakai key
                # semula sesuai §5 "retry hasil tak pasti memakai key semula").
                if isinstance(response, Response) and 200 <= response.status_code < 300:
                    IdempotencyKey.objects.filter(id=claimed_id).update(
                        response_status=response.status_code,
                        response_body=response.data,
                    )
                return response

        return wrapper

    return decorator
