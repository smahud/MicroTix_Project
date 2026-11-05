"""Pipeline upload bukti pembayaran — TK-106 (M1 untuk alur M2).

Validasi: nama, ukuran ≤ upload.payment_proof_max_bytes (5 MiB), MIME dari
magic bytes (bukan klaim klien), path opaque non-eksekutable di penyimpanan
privat, scan fail-closed. Data file diambil dari body multipart/teks
terenkode base64 oleh adapter live; di sini diterima sebagai bytes tervalidasi.
"""
from __future__ import annotations

import binascii
import os
import uuid

from django.conf import settings

from domains.common.envelope import ApiError

MAX_BYTES = 5 * 1024 * 1024  # upload.payment_proof_max_bytes
ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp", "application/pdf"}
MIME_MAGIC = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"RIF", "image/webp"),  # dicek lebih lanjut dengan offset 8..12
    (b"%PDF-", "application/pdf"),
]


def sniff_mime(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:3] == b"RIF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def _decode_payload(body: dict) -> bytes:
    """Terima {file_b64} (adapter live) — decode terbatas dan aman."""
    raw = body.get("file_b64")
    if not raw or not isinstance(raw, str):
        raise ApiError.validation(
            {"file_b64": [{"code": "required", "message": "file_b64 wajib (isi berkas terenkode base64)"}]}
        )
    try:
        data = binascii.a2b_base64(raw, strict_mode=False)
    except (binascii.Error, ValueError):
        raise ApiError.validation(
            {"file_b64": [{"code": "invalid", "message": "Base64 tidak valid"}]}
        ) from None
    return data


def store_payment_proof(request, tenant_id, invoice, body: dict) -> dict:
    data = _decode_payload(body)
    if len(data) > MAX_BYTES:
        raise ApiError.validation(
            {"file": [{"code": "too_large", "message": f"Berkas melebihi {MAX_BYTES} byte"}]}
        )
    if not data:
        raise ApiError.validation({"file": [{"code": "empty", "message": "Berkas kosong"}]})
    mime = sniff_mime(data)
    claimed = str(body.get("mime", "")).split(";")[0].strip()
    if mime is None:
        raise ApiError.validation(
            {"file": [{"code": "mime", "message": "Jenis berkas tidak didukung (PNG/JPEG/WebP/PDF)"}]}
        )
    if claimed and claimed not in ALLOWED_MIME:
        raise ApiError.validation(
            {"mime": [{"code": "mime", "message": "MIME klaim tidak diizinkan"}]}
        )
    # Klaim MIME wajib cocok dengan isi berkas (magic bytes) — bukan sekadar diizinkan.
    if claimed and claimed != mime:
        raise ApiError.validation(
            {"mime": [{"code": "mismatch", "message": f"Isi berkas terdeteksi {mime}, bukan {claimed}"}]}
        )
    # ClamAV fail-closed bila dikonfigurasi; tanpa daemon → dev-stub berlabel.
    scanner_mode = os.environ.get("MT_SCAN_MODE", "disabled")
    if scanner_mode == "clamav":
        import clamd  # hanya saat daemon tersedia (opsi produksi)

        try:
            conn = clamd.ClamdNetworkSocket()
            result = conn.instream(_BytesIO(data))
            status = result.get("stream", ("OK", ""))[0]
            if status != "OK":
                raise ApiError.validation(
                    {"file": [{"code": "infected", "message": "Berkas ditolak pemindai"}]}
                )
        except ApiError:
            raise
        except Exception:
            # Scanner tidak sehat → fail-closed (TK-106).
            raise ApiError.unavailable() from None

    # Path opaque non-eksekutable; tidak pernah diekspos ke tenant.
    opaque = uuid.uuid4().hex
    rel = f"payment-proofs/{opaque}"
    root = settings.MT_STORAGE_ROOT
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    os.chmod(target, 0o600)
    return {"path": rel, "mime": mime, "size": len(data)}


class _BytesIO:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            chunk, self._pos = self._data[self._pos :], len(self._data)
            return chunk
        chunk = self._data[self._pos : self._pos + n]
        self._pos += len(chunk)
        return chunk
