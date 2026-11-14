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
body opaque) TIDAK diubah. Operasi platform memakai scope eksplisit `platform`
yang tidak bergeser ketika operator berpindah active tenant.

Hash body v2 (REV-1311-03): field identitas UUID yang DIDEKLARASIKAN view
(`body_uuid_fields`) dinormalkan ke bentuk canonical sebelum HMAC — ejaan
alias UUID pada body menghasilkan hash yang sama (replay), bukan 409 palsu.
String lain tetap exact-case; elemen list dinormalkan per elemen tanpa
mengubah urutan/semantik array. Kompatibilitas record lama: perbandingan
menerima hash v2 ATAU hash v1 raw — body yang identik byte-per-byte dengan
request aslinya selalu cocok dengan record pra-v2.

Legacy shapes (REV-1311-01/02): migrasi jobs.0004 menormalkan record
pra-0004 ke identitas baru bila dapat direkonsiliasi. Dua bentuk TIDAK dapat
dinormalkan migrasi dan ditangani runtime SEBELUM klaim:
- `payment_submission` resource='' (protokol lama tanpa resource): body sama
  + respons ada → replay setelah replay_guard memverifikasi kepemilikan
  submission/invoice/tenant; verifikasi gagal atau tanpa respons → 409 aman.
- `identity_conflict_resolve` group-only (tanpa migration UUID): tidak dapat
  diikat ke session → 409 aman (`legacy_replay=False`), tidak pernah
  mereplay lintas session.
Record legacy statis (tidak ada penulis baru bentuk ini pasca-migrasi),
jadi pemeriksaan SELECT sebelum INSERT bebas race.
"""
from __future__ import annotations

import functools
import hashlib
import hmac
import json
import uuid as _uuid
from typing import Any, Callable, Iterable

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response

from domains.common.envelope import ApiError
from domains.jobs.models import IdempotencyKey

TTL_S = 7 * 24 * 3600
PLATFORM_SCOPE = "platform"
_CLAIM_ATTEMPTS = 3


def _canonical_uuid_value(value: Any) -> str | None:
    """Canonical lowercase bila value ejaan UUID sah; None bila bukan."""
    if not isinstance(value, str):
        return None
    try:
        return str(_uuid.UUID(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _hash_payload(payload: Any) -> str:
    canonical = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hmac.new(settings.SECRET_KEY.encode(), canonical.encode(), hashlib.sha256).hexdigest()


def _normalize_body(body: Any, uuid_fields: Iterable[str]) -> Any:
    """Salin body dengan field UUID yang dideklarasikan dinormalkan (v2).

    Hanya nilai yang benar-benar ejaan UUID yang diganti; string lain
    (username, kode, opaque) dipertahankan exact-case. List dinormalkan per
    elemen tanpa mengubah urutan (semantik array dipertahankan). Body bukan
    dict dikembalikan apa adanya.
    """
    fields = tuple(uuid_fields)
    if not fields or not isinstance(body, dict):
        return body

    def _canon_or_keep(value: Any) -> Any:
        if isinstance(value, str):
            canon = _canonical_uuid_value(value)
            return canon if canon is not None else value
        return value

    normalized = dict(body)
    for field in fields:
        if field not in normalized:
            continue
        value = normalized[field]
        if isinstance(value, list):
            normalized[field] = [_canon_or_keep(v) for v in value]
        else:
            normalized[field] = _canon_or_keep(value)
    return normalized


def _body_hash(body: Any, uuid_fields: Iterable[str] = ()) -> str:
    """Hash v2 — field UUID dideklarasikan dinormalkan sebelum HMAC."""
    return _hash_payload(_normalize_body(body, uuid_fields))


def _body_hash_legacy(body: Any) -> str:
    """Hash v1 raw — kompatibilitas record pra-v2 / pra-migrasi 0004."""
    return _hash_payload(body)


def _body_matches(record_hash: str, body: Any, uuid_fields: Iterable[str]) -> bool:
    """True bila hash record cocok dengan v2 (normalized) atau v1 (raw) body.

    Perbandingan konstan-waktu (hmac.compare_digest). Record v1 cocok dengan
    body identik byte-per-byte; record v1 yang aslinya sudah canonical juga
    cocok dengan ejaan alias yang sama-sama canonical di v2.
    """
    fields = tuple(uuid_fields)
    candidates = {_body_hash(body, fields), _body_hash_legacy(body)}
    return any(hmac.compare_digest(record_hash, c) for c in candidates)


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
    body_uuid_fields: tuple[str, ...] = (),
    legacy_shapes: Callable[[str], list[str]] | None = None,
    legacy_replay: bool = True,
    replay_guard: Callable[[Any, Any, dict], None] | None = None,
):
    """Dekorator view DRF: claim/replay respons per Idempotency-Key.

    `platform=True` → scope eksplisit `platform` (operasi lintas tenant);
    tidak pernah diambil dari sesi active tenant. Tanpa flag: tenant dari URL
    (kanonikalisasi UUID), fallback sesi active tenant.
    `resource_uuid=False` → resource adalah token opaque exact-case — tidak
    di-kanonikalisasi; validasi bentuk tetap milik domain/view.
    `body_uuid_fields` → nama field body yang memuat identitas UUID
    terstruktur; dinormalkan sebelum hash (v2) supaya ejaan alias tidak
    menjadi konflik palsu (REV-1311-03).
    `legacy_shapes(resource)` → daftar bentuk resource pra-migrasi-0004 yang
    tidak dapat dinormalkan; diperiksa sebelum klaim. `legacy_replay=False`
    → record legacy selalu ditolak aman (target tidak dapat diverifikasi,
    mis. group konflik identitas tanpa migration UUID).
    `replay_guard(request, kwargs, record)` → verifikasi operation-specific
    kepemilikan/target respons cache sebelum replay; raise ApiError.conflict
    bila respons tidak lagi sahih (REV-1311-01).
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
            body = getattr(request, "data", None)
            body_h = _body_hash(body, body_uuid_fields)

            with transaction.atomic():
                # Retensi 7 hari: kelas data cache; business uniqueness
                # domain tetap menjaga duplikasi setelah record terhapus.
                cutoff = timezone.now() - timezone.timedelta(seconds=TTL_S)
                IdempotencyKey.objects.filter(created_at__lt=cutoff).delete()

                # Legacy pra-0004 (REV-1311-01/02): bentuk resource lama yang
                # tidak dapat dinormalkan migrasi diperiksa SEBELUM klaim —
                # tanpa ini klaim INSERT baru berhasil dan efek dieksekusi
                # ulang buta. Record legacy statis: penulis bentuk ini hanya
                # ada pra-migrasi, SELECT di sini bebas race.
                if legacy_shapes is not None:
                    shapes = [s for s in legacy_shapes(resource) if s != resource]
                    if shapes:
                        legacy = (
                            IdempotencyKey.objects.filter(
                                principal=principal,
                                tenant_scope=tenant_part,
                                operation=operation,
                                idem_key=key,
                                resource__in=shapes,
                            )
                            .order_by("-created_at", "-id")
                            .first()
                        )
                        if legacy is not None:
                            if not _body_matches(legacy.body_hash, body, body_uuid_fields):
                                raise ApiError.conflict(
                                    "idempotency_conflict", "error.idempotency_conflict"
                                )
                            if legacy.response_status is None or not legacy_replay:
                                # Efek tak terbukti, atau target tidak dapat
                                # diikat ke identitas baru → tolak aman.
                                raise ApiError.conflict(
                                    "idempotency_conflict", "error.idempotency_conflict"
                                )
                            if replay_guard is not None:
                                replay_guard(request, kwargs, legacy)
                            return Response(
                                legacy.response_body, status=legacy.response_status
                            )

                claimed_id, existing = _claim_id(
                    principal, tenant_part, operation, resource, key, body_h
                )
                if claimed_id is None:
                    if not _body_matches(existing.body_hash, body, body_uuid_fields):
                        raise ApiError.conflict("idempotency_conflict", "error.idempotency_conflict")
                    if existing.response_status is None:
                        # Record terkomit tanpa respons = klaim protokol lama
                        # (pra-migrasi 0004) yang efeknya tak bisa dibuktikan
                        # — tolak aman, jangan eksekusi ulang buta. Rekonsili
                        # asi ops (isi respons sesuai outcome) memulihkan replay.
                        raise ApiError.conflict(
                            "idempotency_conflict", "error.idempotency_conflict"
                        )
                    # Replay respons logis: satu aksi logis, hasil sama.
                    # Guard verifikasi kepemilikan/target respons cache.
                    if replay_guard is not None:
                        replay_guard(request, kwargs, existing)
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
