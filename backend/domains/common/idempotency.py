"""Idempotency-Key untuk mutasi (ARCHITECTURE.md §5; PA-006).

Identity: principal + tenant/platform + operation + canonical resource + key.
Body dibandingkan HMAC; sama+isi sama → replay respons logis; isi berbeda →
409 idempotency_conflict. Retensi 7 hari.

Protokol claim/replay conflict-safe (PA-006):
- Klaim INSERT, eksekusi handler dan persistensi respons terjadi dalam SATU
  transaksi database. Pesaing same-identity INSERT menunggu unique index
  PostgreSQL sampai transaksi pemimpin selesai: commit → pesaing menerima
  unique violation lalu replay respons tersimpan; rollback → pesaing menjadi
  pemimpin dan mengeksekusi segar. Satu aksi logis, tanpa duplicate effect
  dan tanpa unique-violation 500.
- Record tanpa respons (in-flight pra-PA-006 / legacy / handler non-2xx)
  TIDAK dieksekusi ulang buta: ditolak 409 fail-safe; business uniqueness
  domain tetap menjaga efek, dan kunci dapat dipakai ulang setelah TTL.
- Operasi platform memakai target scope eksplisit "platform" yang TIDAK
  berubah ketika operator berpindah active tenant pada sesinya.
- Identitas UUID (tenant/resource) dikanonikalisasi sebelum scope, sehingga
  ejaan alias (huruf besar/kecil, tanpa hyphen, urn) dari target yang sama
  menghasilkan scope yang sama; resource id salah bentuk → 422.
- Auth/membership/permission/sensitive step-up tetap diperiksa oleh
  initial() view SEBELUM dekorator pada SETIAP permintaan, termasuk replay:
  respons tersimpan tidak pernah dibocorkan melewati pemeriksaan itu.
"""
from __future__ import annotations

import functools
import hashlib
import hmac
import json
import uuid as uuid_mod
from typing import Any, Callable

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from rest_framework.response import Response

from domains.common.envelope import ApiError
from domains.jobs.models import IdempotencyKey

TTL_S = 7 * 24 * 3600

#: Target scope operasi platform (di luar konteks tenant mana pun).
PLATFORM_SCOPE = "platform"

#: Percobaan klaim maksimum: 2 cukup untuk race purge-TTL yang nyaris mustahil.
_MAX_CLAIM_ATTEMPTS = 2


def _body_hash(body: Any) -> str:
    canonical = json.dumps(body or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hmac.new(settings.SECRET_KEY.encode(), canonical.encode(), hashlib.sha256).hexdigest()


def _principal(request) -> str:
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return str(user.id)
    return "anonymous"


def _canonical_uuid(field: str, value: str) -> str:
    """Kanonikalisasi identitas UUID terstruktur; salah bentuk → 422.

    Ejaan alias (huruf besar, tanpa hyphen, urn/braces) dari identitas yang
    sama dipetakan ke SATU bentuk kanonik sehingga scope idempotency sama.
    """
    try:
        return str(uuid_mod.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        raise ApiError.validation(
            {field: [{"code": "invalid", "message": f"{field} harus UUID"}]}
        ) from None


def _scope_target(kwargs) -> str:
    """Target scope: tenant kanonik dari route, atau "platform" eksplisit.

    Route platform (tanpa tenant_id) memakai konstanta — bukan active tenant
    sesi — sehingga scope aksi platform tidak berubah ketika operator
    berpindah tenant aktif (PA-006).
    """
    tenant_id = kwargs.get("tenant_id")
    if tenant_id:
        return _canonical_uuid("tenant_id", tenant_id)
    return PLATFORM_SCOPE


def _purge_expired() -> None:
    """Hapus record kedaluwarsa (retensi 7 hari) tanpa memblok pesaing.

    FOR UPDATE SKIP LOCKED: pembersihan konkuren tidak menunggu transaksi
    lain yang memegang baris kedaluwarsa, sehingga jalur klaim tidak
    terserialisasi tambahan oleh pembersihan.
    """
    cutoff = timezone.now() - timezone.timedelta(seconds=TTL_S)
    with connection.cursor() as cur:
        cur.execute(
            "DELETE FROM jobs_idempotency_key WHERE id IN ("
            "SELECT id FROM jobs_idempotency_key WHERE created_at < %s "
            "FOR UPDATE SKIP LOCKED)",
            [cutoff],
        )


def _committed_record(principal: str, scope: str, key: str) -> IdempotencyKey | None:
    return IdempotencyKey.objects.filter(principal=principal, scope=scope, idem_key=key).first()


def _replay_or_reject(record: IdempotencyKey, body_h: str) -> Response:
    """Tindak lanjut record milik identitas ini: replay atau tolak fail-safe."""
    if record.body_hash != body_h:
        raise ApiError.conflict("idempotency_conflict", "error.idempotency_conflict")
    if record.response_status is not None:
        return Response(record.response_body, status=record.response_status)
    # Record tanpa respons: in-flight pra-PA-006 / terputus / legacy.
    # Tidak blind-execute — efek tidak dapat dibuktikan dari record ini.
    # Fail-safe 409 (kode kontrak existing); business uniqueness domain
    # tetap menjaga efek ganda; kunci bebas dipakai setelah TTL.
    raise ApiError.conflict("idempotency_conflict", "error.idempotency_conflict")


def idempotent(
    operation: str,
    resource_from: Callable[[Any, Any], str] | None = None,
    *,
    resource_is_uuid: bool = True,
):
    """Dekorator view DRF: klaim/replay respons per Idempotency-Key.

    ``resource_from(request, kwargs)`` menentukan resource kanonik operasi
    (default: kwargs ``resource_id``; kosong untuk operasi pembuatan).
    ``resource_is_uuid=False`` untuk resource id non-UUID yang opaque dan
    sudah kanonik (mis. token hex grup konflik identitas).
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
            target = _scope_target(kwargs)
            resource = resource_from(request, kwargs) if resource_from else kwargs.get("resource_id", "")
            resource = str(resource or "")
            if resource and resource_is_uuid:
                resource = _canonical_uuid("resource_id", resource)
            scope = f"{operation}:{target}:{resource}"
            body_h = _body_hash(getattr(request, "data", None))

            _purge_expired()

            for _attempt in range(_MAX_CLAIM_ATTEMPTS):
                claim_inserted = False
                try:
                    # SATU transaksi: klaim + handler + persistensi respons.
                    # Untuk view tenant ini savepoint dalam transaksi
                    # tenant_scope; untuk view platform ini transaksi terluar.
                    with transaction.atomic():
                        IdempotencyKey.objects.create(
                            principal=principal,
                            scope=scope,
                            idem_key=key,
                            body_hash=body_h,
                        )
                        claim_inserted = True
                        response = func(self, request, *args, **kwargs)
                        if isinstance(response, Response) and 200 <= response.status_code < 300:
                            IdempotencyKey.objects.filter(
                                principal=principal, scope=scope, idem_key=key
                            ).update(
                                response_status=response.status_code,
                                response_body=response.data,
                            )
                        return response
                except IntegrityError:
                    if claim_inserted:
                        # IntegrityError bisnis dari handler (bukan klaim) —
                        # biarkan menggelembung sebagaimana semula.
                        raise
                    record = _committed_record(principal, scope, key)
                    if record is not None:
                        return _replay_or_reject(record, body_h)
                    # Baris pesaing hilang (race purge TTL) — coba klaim lagi.
            raise ApiError.conflict("idempotency_conflict", "error.idempotency_conflict")

        return wrapper

    return decorator
