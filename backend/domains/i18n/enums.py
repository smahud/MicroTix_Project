"""Enumerasi lokal untuk /meta/enums (I18N-06).

Grup dan nilai mengikuti state domain ARCHITECTURE.md §7 dan kontrak
frontend (apps/web/src/api/mock/adapter.ts getEnums) agar UI live konsisten.
"""
from __future__ import annotations

ENUMS_ID: dict[str, dict[str, str]] = {
    "job_state": {
        "queued": "Permintaan diterima dan menunggu giliran",
        "claimed": "Sedang diproses",
        "preflight": "Sedang diproses",
        "executing": "Sedang diproses",
        "verifying": "Memeriksa hasil sesuai jenis tindakan",
        "waiting_dependency": "Menunggu dependency yang disebutkan pada pekerjaan",
        "retry_wait": "Akan dicoba lagi otomatis",
        "uncertain": "Hasil perubahan belum dapat dipastikan",
        "recovery_required": "Perlu pemulihan manual sebelum melanjutkan",
        "succeeded": "Pekerjaan selesai; hasil telah diverifikasi",
        "failed": "Gagal",
        "cancelled": "Dibatalkan",
    },
    "enforcement_mode": {
        "local": "Lokal",
        "radius_shadow": "Bayangan",
        "radius_authoritative": "Otoritatif",
        "degraded": "Terganggu",
    },
    "connection": {"online": "Online", "offline": "Offline", "unknown": "Tidak diketahui"},
    "isolation": {
        "normal": "Normal",
        "isolated": "Terisolir",
        "awaiting_verification": "Menunggu verifikasi",
        "hold": "Hold",
    },
    "payment": {
        "unbilled": "Belum dibayar",
        "partial": "Sebagian",
        "paid": "Lunas",
        "not_billed": "Tidak ditagih",
    },
    "lifecycle": {
        "draft": "Draft",
        "pending": "Menunggu",
        "provisioning": "Menyiapkan",
        "provisioned": "Aktif",
        "conflict": "Konflik",
        "failed": "Gagal",
        "terminated": "Dihentikan",
        "archived": "Diarsipkan",
    },
}

# Placeholder en: terjemahan penuh menungui siklus i18n; struktur kunci identik.
ENUMS_EN: dict[str, dict[str, str]] = {
    group: {
        key: {"queued": "Request accepted and waiting", "succeeded": "Job finished; result verified"}.get(key, label)
        for key, label in values.items()
    }
    for group, values in ENUMS_ID.items()
}


def enums_for(locale: str) -> dict[str, dict[str, str]]:
    return ENUMS_EN if locale == "en" else ENUMS_ID
