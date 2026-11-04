# Keputusan pemilik yang tersisa

Supporting decision request; belum menjadi aturan produk. B01/B02 telah ditutup oleh EXE-01/02 sesuai kelanjutan rekomendasi pemilik. Keputusan berikut ditemukan dari pembacaan requirement ASVS terpin, bukan dari asumsi risiko umum.

## SEC-DEC-01 — Assurance login tenant dan ASVS5.0.0 V6.3.3

Status: NEEDS_OWNER_DECISION. Severity: HIGH untuk final security-contract/G2; tidak memblokir pembuatan verifier, toolchain, fixture dan kontrak lokal yang independen.

Sumber: PRD §2 mewajibkan MFA untuk peran platform dan sebelum aksi sensitif; AUD-15 memperluas step-up sensitif ke setiap aktor berizin. ASVS v5.0.0-6.3.3 L2 mensyaratkan MFA atau kombinasi mekanisme autentikasi untuk akses aplikasi; relaksasi memerlukan rationale lengkap dan mitigating controls. Sumber tidak secara eksplisit menetapkan assurance login biasa seluruh operator/portal tenant. Implementer tidak boleh memilih kebijakan baru diam-diam.

Pilihan yang direkomendasikan: wajibkan password+TOTP (atau recovery code sekali pakai sesuai proses pemulihan) sebelum sesi operator tenant memperoleh akses data; enrolment factor/recovery dibatasi autentikasi dan audit; semua peran platform tetap wajib MFA. Portal pelanggan/agen/kolektor juga harus memiliki disposition assurance eksplisit: faktor tambahan atau exception terpisah yang direview; jangan mengecualikan portal dengan hanya mengganti namanya. Perubahan ini menambah kewajiban pengguna sehingga memerlukan persetujuan owner; desain recovery dan sumber ASVS tetap harus diuji.

Alternatif: pertahankan login biasa sesuai baseline, susun exception ASVS6.3.3 dengan threat model, scope aktor, kontrol kompensasi, acceptance risiko dan reviewer keamanan; tidak mengklaim conformant ASVS L2 tanpa evaluasi exception. Rate limiting saja tidak otomatis memenuhi requirement tersebut.

Keputusan yang diminta: pilih cakupan wajib MFA pada operator/portal, atau setujui scope exception beserta pemilik risiko. Setelah keputusan: amend master/PRD/TD, perbarui TK-101/102, cases QA-SEC-02/04/15 dan ASVS6.3.3, ulangi review dan seal pada revisi baru. Tidak ada keputusan atau tanda tangan yang dipalsukan dalam paket ini.

Proposed patch utama (belum diterapkan): tambahkan pada PRD §2 “Sesi akses data seluruh operator tenant memerlukan password dan faktor TOTP; recovery code sekali pakai melalui alur pemulihan berversi bukan bypass tetap. Portal memakai assurance yang secara eksplisit disetujui.” Scope portal harus diputuskan sebelum patch ini dapat difinalkan. Ketentuan sesi/step-up/last Owner dan role boundaries tidak dilonggarkan.
