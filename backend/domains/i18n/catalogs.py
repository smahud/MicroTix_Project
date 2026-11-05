"""Katalog pesan backend id/en — I18N.md.

Kunci stabil; fallback 'id' (I18N-05). Pesan mesin (error envelope,
email transaksional, label enum API) memakai katalog ini, bukan string keras.
"""
from __future__ import annotations

CATALOGS: dict[str, dict[str, str]] = {
    "id": {
        "error.validation": "Periksa kembali isian Anda",
        "error.unauthenticated": "Sesi berakhir. Masuk kembali",
        "error.unauthorized": "Email atau password tidak cocok",
        "error.forbidden": "Anda tidak memiliki izin untuk tindakan ini",
        "error.not_found": "Data tidak ditemukan",
        "error.conflict": "Operasi berkonflik dengan kondisi saat ini",
        "error.rate_limited": "Terlalu banyak percobaan. Coba lagi nanti",
        "error.dependency_unavailable": "Layanan belum tersedia",
        "error.idempotency_conflict": "Idempotency-Key sama dipakai untuk isi permintaan berbeda",
        "error.revision_conflict": "Data telah berubah sejak terakhir dibaca",
        "enrollment.token_invalid": "Token enrollment tidak valid",
        "enrollment.token_expired": "Token enrollment kedaluwarsa — minta token baru",
        "enrollment.router_code_taken": "Kode router sudah dipakai",
        "enrollment.router_code_active": "Kode router masih memiliki enrollment aktif",
        "enrollment.not_active": "Enrollment tidak lagi aktif",
        "enrollment.identity_conflict": "Identitas router berbeda dengan yang terdaftar",
        "enrollment.source_not_verified": "Permintaan harus berasal dari alamat tunnel yang direservasi",
        "enrollment.wg_host_not_configured": "WireGuard host belum dikonfigurasi",
        "enrollment.tunnel_pool_exhausted": "Kapasitas alamat tunnel habis",
        "access.username_taken": "Username sudah dipakai pada tenant ini",
        "access.password_too_short": "Password layanan minimal 8 karakter",
        "access.invalid_state": "State akun tidak sah",
        "access.credential_unknown": "Kredensial akun ini tidak tersedia",
        "access.no_access_account": "Layanan tidak memiliki akun akses",
        "error.quota_exceeded": "Kuota paket telah terlampaui",
        "error.uncertain": "Hasil perubahan belum dapat dipastikan",
        "auth.login_mismatch": "Email atau password tidak cocok",
        "auth.totp_invalid": "Kode verifikasi tidak valid",
        "auth.reauth_failed": "Konfirmasi identitas gagal",
        "auth.mfa_required": "Aktifkan MFA terlebih dahulu",
        "auth.token_invalid": "Tautan tidak valid atau telah kedaluwarsa",
        "auth.rate_limited": "Terlalu banyak percobaan login. Coba lagi nanti",
        "team.last_owner": "Owner terakhir tidak dapat dihapus atau diturunkan",
        "job.not_cancellable": "Pekerjaan sudah berjalan dan tidak dapat dibatalkan",
        "job.not_retryable": "Pekerjaan tidak dapat diulang",
        "subscription.no_upgrade": "Perubahan paket tidak tersedia",
    },
    "en": {
        "error.validation": "Please check your input",
        "error.unauthenticated": "Session ended. Please sign in again",
        "error.unauthorized": "Email or password does not match",
        "error.forbidden": "You do not have permission for this action",
        "error.not_found": "Data not found",
        "error.conflict": "Operation conflicts with current state",
        "error.rate_limited": "Too many attempts. Try again later",
        "error.dependency_unavailable": "Service is not available yet",
        "error.idempotency_conflict": "Idempotency-Key reused with different request body",
        "error.revision_conflict": "Data has changed since it was read",
        "enrollment.token_invalid": "Enrollment token is not valid",
        "enrollment.token_expired": "Enrollment token has expired — request a new one",
        "enrollment.router_code_taken": "Router code is already in use",
        "enrollment.router_code_active": "Router code still has an active enrollment",
        "enrollment.not_active": "Enrollment is no longer active",
        "enrollment.identity_conflict": "Router identity differs from the registered one",
        "enrollment.source_not_verified": "Request must originate from the reserved tunnel address",
        "enrollment.wg_host_not_configured": "Host WireGuard is not configured yet",
        "enrollment.tunnel_pool_exhausted": "Tunnel address capacity exhausted",
        "access.username_taken": "Username is already used in this tenant",
        "access.password_too_short": "Service password must be at least 8 characters",
        "access.invalid_state": "Invalid account state",
        "access.credential_unknown": "Credentials for this account are unavailable",
        "access.no_access_account": "Service has no access account",
        "error.quota_exceeded": "Plan quota has been exceeded",
        "error.uncertain": "Change outcome could not be determined",
        "auth.login_mismatch": "Email or password does not match",
        "auth.totp_invalid": "Verification code is not valid",
        "auth.reauth_failed": "Identity confirmation failed",
        "auth.mfa_required": "Enable MFA first",
        "auth.token_invalid": "Link is invalid or has expired",
        "auth.rate_limited": "Too many login attempts. Try again later",
        "team.last_owner": "The last Owner cannot be removed or demoted",
        "job.not_cancellable": "Job is already running and cannot be cancelled",
        "job.not_retryable": "Job cannot be retried",
        "subscription.no_upgrade": "Plan change is not available",
    },
}


def message(key: str, locale: str = "id", **kwargs) -> str:
    catalog = CATALOGS.get(locale) or CATALOGS["id"]
    text = catalog.get(key) or CATALOGS["id"].get(key, key)
    if kwargs:
        for name, value in kwargs.items():
            text = text.replace("{" + name + "}", str(value))
    return text
