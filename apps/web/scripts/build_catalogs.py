#!/usr/bin/env python3
"""Builder katalog pesan MicroTix (locales/{id,en}/web.json).

Sumber kebenaran: pasangan (id, en) di bawah — I18N.md §3:
katalog per bahasa per domain `web`, makna dan placeholder sama.
Jalankan: python3 apps/web/scripts/build_catalogs.py
"""
import json
from pathlib import Path

LOCALES = Path(__file__).resolve().parents[3] / 'locales'

# key: (id, en)
MSGS: dict[str, tuple[str, str]] = {}

def add(key: str, id_text: str, en_text: str) -> None:
    assert key not in MSGS, f'duplikat kunci: {key}'
    MSGS[key] = (id_text, en_text)

# ============ app ============
add('app.skip_to_content', 'Lewati ke konten utama', 'Skip to main content')
add('app.open_menu', 'Buka menu navigasi', 'Open navigation menu')
add('app.user_menu', 'Menu pengguna', 'User menu')
add('app.logout', 'Keluar', 'Sign out')
add('app.back_to_landing', 'Kembali ke halaman utama', 'Back to landing page')
add('app.brand_sub', 'Manajemen RT/RW Net', 'RT/RW Net management')
add('app.dev_mock_banner', 'MODE PENGEMBANGAN: data yang ditampilkan adalah fixture simulasi — bukan integrasi backend.', 'DEVELOPMENT MODE: displayed data is simulated fixture — not a backend integration.')

# ============ common ============
add('common.cancel', 'Batal', 'Cancel')
add('common.close', 'Tutup', 'Close')
add('common.close_dialog', 'Tutup dialog', 'Close dialog')
add('common.close_panel', 'Tutup panel', 'Close panel')
add('common.continue', 'Lanjutkan', 'Continue')
add('common.back', 'Kembali', 'Back')
add('common.back_to_list', 'Kembali ke daftar', 'Back to list')
add('common.copy', 'Salin', 'Copy')
add('common.copied', 'Disalin', 'Copied')
add('common.dismiss', 'Tutup notifikasi', 'Dismiss notification')
add('common.loading', 'Memuat…', 'Loading…')
add('common.unknown', 'tidak diketahui', 'unknown')
add('common.not_set', 'belum diisi', 'not set')
add('common.not_found', 'Data tidak ditemukan.', 'Data not found.')
add('common.error_generic', 'Terjadi kesalahan. Coba beberapa saat lagi.', 'Something went wrong. Please try again later.')
add('common.yes', 'Ya', 'Yes')
add('common.no', 'Tidak', 'No')
add('common.prev_page', 'Sebelumnya', 'Previous')
add('common.next_page', 'Berikutnya', 'Next')
add('common.page_info', '{count} item ditampilkan', '{count} item{count, plural, =0 {} one {} other {s}} shown')
add('common.all_routers', 'Semua router', 'All routers')
add('common.all_statuses', 'Semua status', 'All statuses')
add('common.clear_filters', 'Hapus filter', 'Clear filters')

# ============ table ============
add('table.select_all', 'Pilih semua baris di halaman ini', 'Select all rows on this page')
add('table.select_row', 'Pilih baris', 'Select row')
add('table.empty_title', 'Belum ada data', 'No data yet')
add('table.error_title', 'Data gagal dimuat', 'Failed to load data')

# ============ permission ============
add('permission.title', 'Aksi memerlukan izin', 'Action requires permission')
add('permission.contact_owner', 'Hubungi Owner perusahaan Anda untuk akses.', 'Contact your company Owner for access.')
add('permission.contact_owner_with', 'Hubungi {who} untuk akses.', 'Contact {who} for access.')
add('permission.admin_only', 'Ruang ini hanya untuk administrator platform.', 'This workspace is for platform administrators only.')
add('permission.routers_enroll', 'Menghubungkan router memerlukan izin routers.enroll.', 'Connecting a router requires the routers.enroll permission.')
add('permission.migration_run', 'Menjalankan migrasi memerlukan izin migration.run.', 'Running a migration requires the migration.run permission.')
add('permission.imports_run', 'Impor CSV memerlukan izin imports.run.', 'CSV import requires the imports.run permission.')
add('permission.backups_run', 'Backup memerlukan izin backups.run.', 'Backups require the backups.run permission.')
add('permission.radius_cutover', 'Cutover RADIUS memerlukan izin radius.cutover.', 'RADIUS cutover requires the radius.cutover permission.')

# ============ role ============
for r, (a, b) in {
    'owner': ('Owner', 'Owner'),
    'technician': ('Teknisi', 'Technician'),
    'payments_admin': ('Admin Pembayaran', 'Payments Admin'),
    'accountant': ('Akuntan', 'Accountant'),
    'viewer': ('Viewer', 'Viewer'),
    'collector': ('Kolektor', 'Collector'),
    'agent': ('Agen', 'Agent'),
}.items():
    add(f'role.{r}', a, b)

# ============ tenant ============
add('tenant.switch_label', 'Pilih perusahaan', 'Choose company')
add('tenant.switched_to', 'Berpindah ke {name}', 'Switched to {name}')
add('tenant.switch_dirty_confirm', 'Ada formulir yang belum tersimpan. Simpan dulu atau batalkan perubahan sebelum berpindah perusahaan?', 'You have an unsaved form. Save it or discard changes before switching company?')

# ============ nav ============
add('nav.group.operational', 'Operasional', 'Operations')
add('nav.group.network', 'Jaringan', 'Network')
add('nav.group.finance', 'Keuangan', 'Finance')
add('nav.group.company', 'Perusahaan', 'Company')
add('nav.group.help', 'Bantuan', 'Help')
add('nav.overview', 'Beranda', 'Home')
add('nav.customers', 'Pelanggan', 'Customers')
add('nav.packages', 'Paket dan Profile', 'Plans and Profiles')
add('nav.billing', 'Tagihan dan Pembayaran', 'Billing and Payments')
add('nav.incidents', 'Gangguan dan Teknisi', 'Incidents and Technicians')
add('nav.jobs', 'Pusat Pekerjaan', 'Job Center')
add('nav.routers', 'Router dan Monitoring', 'Routers and Monitoring')
add('nav.radius', 'Basis Akun RADIUS', 'RADIUS Account Base')
add('nav.backups', 'Backup', 'Backups')
add('nav.devices', 'Perangkat ACS', 'ACS Devices')
add('nav.inventory', 'Inventaris dan Peta', 'Inventory and Map')
add('nav.configuration', 'Konfigurasi', 'Configuration')
add('nav.finance', 'Keuangan', 'Finance')
add('nav.team', 'Perusahaan dan Tim', 'Company and Team')
add('nav.subscription', 'Paket Aplikasi', 'Application Plan')
add('nav.help', 'Bantuan', 'Help')
add('nav.main_nav', 'Navigasi utama', 'Main navigation')

# ============ auth ============
add('auth.login_title', 'Masuk', 'Sign in')
add('auth.login_sub', 'Masuk untuk mengelola perusahaan RT/RW Net Anda.', 'Sign in to manage your RT/RW Net company.')
add('auth.login_submit', 'Masuk', 'Sign in')
add('auth.login_mismatch', 'Email atau password tidak cocok', 'Email or password does not match')
add('auth.field_email', 'Email', 'Email')
add('auth.field_password', 'Password', 'Password')
add('auth.field_totp', 'Kode verifikasi (TOTP)', 'Verification code (TOTP)')
add('auth.forgot_password', 'Lupa password?', 'Forgot password?')
add('auth.no_account', 'Belum punya akun?', 'No account yet?')
add('auth.has_account', 'Sudah punya akun?', 'Already have an account?')
add('auth.register_link', 'Daftar sekarang', 'Register now')
add('auth.totp_title', 'Verifikasi dua langkah', 'Two-step verification')
add('auth.totp_sub', 'Masukkan kode 6 digit dari aplikasi autentikator Anda.', 'Enter the 6-digit code from your authenticator app.')
add('auth.totp_submit', 'Verifikasi', 'Verify')
add('auth.totp_invalid', 'Kode tidak valid. Coba lagi.', 'Invalid code. Try again.')
add('auth.totp_recovery_hint', 'Kode pemulihan sekali pakai dapat dipakai bila perangkat hilang.', 'One-time recovery codes can be used if your device is lost.')
add('auth.register_title', 'Buat akun baru', 'Create a new account')
add('auth.register_sub', 'Perusahaan Anda terpisah dan tidak terlihat oleh perusahaan lain.', 'Your company is isolated and invisible to other companies.')
add('auth.register_submit', 'Daftar', 'Register')
add('auth.field_full_name', 'Nama lengkap', 'Full name')
add('auth.field_company', 'Nama perusahaan', 'Company name')
add('auth.company_helper', 'Nama RT/RW Net Anda, mis. RT Net Melati. Bisa diganti nanti.', 'Your RT/RW Net name, e.g. Melati Net. Changeable later.')
add('auth.password_helper', 'Minimal {count} karakter.', 'At least {count} characters.')
add('auth.strength_label', 'Kekuatan password', 'Password strength')
add('auth.strength_weak', 'Lemah', 'Weak')
add('auth.strength_good', 'Cukup', 'Fair')
add('auth.strength_strong', 'Kuat', 'Strong')
add('auth.register_done_title', 'Periksa email Anda', 'Check your email')
add('auth.register_done_sub', 'Tautan verifikasi telah dikirim. Verifikasi email untuk melanjutkan.', 'A verification link has been sent. Verify your email to continue.')
add('auth.verify_title', 'Verifikasi email', 'Email verification')
add('auth.verify_sub', 'Verifikasi alamat email Anda melalui tautan yang dikirim.', 'Verify your email address via the link that was sent.')
add('auth.verify_submit', 'Verifikasi sekarang', 'Verify now')
add('auth.verify_ok', 'Email terverifikasi. Anda dapat masuk.', 'Email verified. You can sign in.')
add('auth.verify_error', 'Tautan tidak valid atau kedaluwarsa.', 'Link is invalid or expired.')
add('auth.verify_missing_token', 'Tautan tidak memuat token verifikasi.', 'The link does not contain a verification token.')
add('auth.recover_title', 'Pemulihan akun', 'Account recovery')
add('auth.recover_sub', 'Masukkan email Anda untuk menerima tautan pemulihan.', 'Enter your email to receive a recovery link.')
add('auth.recover_submit', 'Kirim tautan pemulihan', 'Send recovery link')
add('auth.recover_sent', 'Jika email terdaftar, tautan telah dikirim', 'If the email is registered, the link has been sent')
add('auth.footer_note', 'Password minimal 12 karakter. MFA direkomendasikan untuk seluruh operator.', 'Password minimum 12 characters. MFA recommended for all operators.')
add('auth.reauth_required_note', 'Aksi sensitif memerlukan konfirmasi identitas (password + TOTP), berlaku 10 menit.', 'Sensitive actions require identity confirmation (password + TOTP), valid for 10 minutes.')
add('auth.reauth_password', 'Password Anda', 'Your password')
add('auth.reauth_cta', 'Konfirmasi identitas sekarang', 'Confirm your identity now')
add('auth.reauth_failed', 'Konfirmasi identitas gagal. Periksa password dan kode TOTP.', 'Identity confirmation failed. Check your password and TOTP code.')
add('auth.reauth_window_note', 'Konfirmasi berlaku 10 menit sejak sukses.', 'Confirmation is valid for 10 minutes after success.')

# ============ landing ============
add('landing.login', 'Masuk', 'Sign in')
add('landing.register', 'Daftar', 'Register')
add('landing.hero_title', 'Kelola RT/RW Net Anda dari satu tempat bersama {brand}', 'Run your RT/RW Net from one place with {brand}')
add('landing.hero_sub', 'Hubungkan MikroTik, adopsi pelanggan existing tanpa input ulang, dan kelola pelanggan, tagihan, pembukuan, backup, serta monitoring — tanpa memutus layanan pelanggan.', 'Connect your MikroTik router, adopt existing customers without re-entry, and manage customers, billing, bookkeeping, backups, and monitoring — without cutting customer service.')
add('landing.cta_start_free', 'Mulai gratis', 'Start free')
add('landing.cta_login', 'Masuk', 'Sign in')
add('landing.publication_note', 'Catatan pengembangan: domain, logo, dan kontak publik belum dikonfigurasi; halaman ini belum dipublikasikan.', 'Development note: public domain, logo, and contact are not configured; this page is not published.')
add('landing.benefits_title', 'Kenapa {brand}?', 'Why {brand}?')
add('landing.benefit_adopt_title', 'Adopsi pelanggan existing', 'Adopt existing customers')
add('landing.benefit_adopt_desc', 'Pindai akun PPPoE/Hotspot di router Anda dan simpan ke basis pengguna perusahaan — tanpa menulis ke router.', 'Scan PPPoE/Hotspot accounts on your router and store them in your company user base — without writing to the router.')
add('landing.benefit_customers_title', 'Manajemen pelanggan', 'Customer management')
add('landing.benefit_customers_desc', 'Satu baris per layanan: status bayar, isolir, koneksi, dan pekerjaan terpisah dan jelas.', 'One row per service: payment, isolation, connection, and job statuses kept separate and clear.')
add('landing.benefit_radius_title', 'RADIUS per perusahaan', 'RADIUS per company')
add('landing.benefit_radius_desc', 'Identitas pelanggan milik perusahaan Anda, bukan perangkat. Ganti router tanpa input ulang akun.', 'Customer identity belongs to your company, not the device. Replace routers without re-entering accounts.')
add('landing.benefit_backup_title', 'Backup terjadwal', 'Scheduled backups')
add('landing.benefit_backup_desc', 'Backup terenkripsi per router dengan retensi 100 generasi rutin terakhir.', 'Encrypted backups per router with the last 100 routine generations retained.')
add('landing.pricing_title', 'Paket harga', 'Pricing')
add('landing.pricing_sub', 'Dua batas terpisah: jumlah router dan jumlah layanan. Harga final tanpa biaya tersembunyi.', 'Two separate limits: router count and service count. Final prices with no hidden fees.')
add('landing.term_toggle', 'Pilih periode pembayaran', 'Choose billing term')
add('landing.term_monthly', 'Bulanan', 'Monthly')
add('landing.term_yearly', 'Tahunan', 'Yearly')
add('landing.yearly_note', 'Tahunan: 12 bulan dibayar setara 10 bulan.', 'Yearly: 12 months billed as 10 months.')
add('landing.price_free', 'Gratis', 'Free')
add('landing.per_month', 'per bulan', 'per month')
add('landing.per_year', 'per tahun', 'per year')
add('landing.plan_popular', 'Populer', 'Popular')
add('landing.plan_choose', 'Pilih paket', 'Choose plan')
add('landing.routers_limit', '{count} router', '{count} router{count, plural, one {} other {s}}')
add('landing.routers_unlimited', 'Router tanpa batas lisensi', 'Unlimited licensed routers')
add('landing.services_limit', '{count} layanan', '{count} service{count, plural, one {} other {s}}')
add('landing.services_unlimited', 'Layanan tanpa batas lisensi', 'Unlimited licensed services')
add('landing.platinum_fair_use_note', 'Platinum: tanpa batas lisensi, bukan tanpa batas operasional (plafon default 25 router / 5.000 layanan per perusahaan).', 'Platinum: unlimited licenses, not unlimited operations (default ceiling 25 routers / 5,000 services per company).')
for p, (a, b) in {
    'free': ('Free', 'Free'), 'bronze': ('Bronze', 'Bronze'), 'silver': ('Silver', 'Silver'),
    'gold': ('Gold', 'Gold'), 'diamond': ('Diamond', 'Diamond'), 'platinum': ('Platinum', 'Platinum'),
}.items():
    add(f'landing.plan_{p}', a, b)

# ============ overview (U03) ============
add('overview.title', 'Beranda', 'Home')
add('overview.description', 'Pekerjaan harian Anda: apa yang perlu ditindaklanjuti hari ini.', 'Your daily work: what needs follow-up today.')
add('overview.period_now', 'Periode saat ini', 'Current period')
add('overview.onboarding_title', 'Onboarding', 'Onboarding')
add('overview.onboarding_progress', '{done} dari {total} langkah selesai', '{done} of {total} steps completed')
add('overview.onboard_company', 'Buat perusahaan', 'Create company')
add('overview.onboard_router', 'Hubungkan router', 'Connect a router')
add('overview.onboard_adopt', 'Adopsi akun', 'Adopt accounts')
add('overview.onboard_map', 'Petakan paket', 'Map plans')
add('overview.onboard_billing', 'Lengkapi tagihan', 'Complete billing')
add('overview.onboard_billing_note', 'Tersedia pada rilis keuangan (R2); tidak memblokir onboarding.', 'Available in the finance release (R2); does not block onboarding.')
add('overview.onboard_team', 'Undang tim', 'Invite your team')
add('overview.onboard_cta', 'Kerjakan →', 'Do it →')
add('overview.work_title', 'Perlu dikerjakan', 'Needs your attention')
add('overview.work_clear', 'Tidak ada pekerjaan tertunda. Semua sehat.', 'No pending work. All clear.')
add('overview.work_card_label', 'Tindakan berikutnya', 'Next action')
add('overview.work_card_cta', 'Buka daftar terkait →', 'Open related list →')
add('overview.work_backup_failed', 'Backup gagal: {count} router', 'Backup failed: {count} router{count, plural, one {} other {s}}')
add('overview.work_radius_issue', 'RADIUS bermasalah: {count} router', 'RADIUS issues: {count} router{count, plural, one {} other {s}}')
add('overview.work_incomplete', 'Data belum lengkap: {count} layanan', 'Incomplete data: {count} service{count, plural, one {} other {s}}')
add('overview.work_router_health', 'Kesehatan router perlu diperiksa: {count} router', 'Router health needs checking: {count} router{count, plural, one {} other {s}}')
add('overview.summary_title', 'Ringkasan usaha', 'Business summary')
add('overview.summary_r1_note', 'Kartu tagihan, kas, dan piutang tersedia pada rilis keuangan (R2) — tidak ditampilkan sebagai nol.', 'Billing, cash, and receivable cards arrive in the finance release (R2) — not shown as zero.')
add('overview.metric_services', 'Layanan aktif', 'Active services')
add('overview.metric_services_hint', 'Total layanan di seluruh router', 'Total services across all routers')
add('overview.metric_routers', 'Router terhubung', 'Connected routers')
add('overview.metric_routers_hint', 'VPN dan API terverifikasi', 'VPN and API verified')
add('overview.metric_accounts', 'Akun RADIUS', 'RADIUS accounts')
add('overview.metric_accounts_hint', 'Basis pengguna perusahaan', 'Company user base')
add('overview.pending_agg_note', 'Agregat diperbarui berkala — lihat daftar transaksi untuk angka terkini', 'Aggregates refresh periodically — see the transaction list for current figures')
add('overview.network_title', 'Kesehatan jaringan', 'Network health')
add('overview.source_collector', 'kolektor', 'collector')
add('overview.traffic_chart_caption', 'Trafik WAN agregat', 'Aggregate WAN traffic')
add('overview.monitoring_partial_banner', 'Sebagian data pemantauan usang atau tidak tersedia. Bukan berarti router mati.', 'Some monitoring data is stale or unavailable. This does not mean routers are down.')
add('overview.open_monitoring', 'Buka monitoring', 'Open monitoring')
add('overview.recent_title', 'Aktivitas terbaru', 'Recent activity')
add('overview.view_job', 'Lihat pekerjaan', 'View job')
add('overview.all_jobs', 'Semua pekerjaan', 'All jobs')
add('overview.empty_tenant_title', 'Perusahaan Anda siap — mulai dengan router pertama', 'Your company is ready — start with your first router')
add('overview.empty_tenant_desc', 'Hubungkan MikroTik pertama Anda untuk mulai memindai dan mengadopsi pelanggan existing.', 'Connect your first MikroTik to start scanning and adopting existing customers.')
add('overview.cta_connect_router', 'Hubungkan router', 'Connect a router')

# ============ customers (U04) ============
add('customers.title', 'Pelanggan', 'Customers')
add('customers.description', '{services} layanan dari {customers} pelanggan unik', '{services} service{services, plural, one {} other {s}} from {customers} unique customer{customers, plural, one {} other {s}}')
add('customers.add', 'Tambah pelanggan', 'Add customer')
add('customers.add_title', 'Tambah pelanggan baru', 'Add a new customer')
add('customers.search_placeholder', 'Cari nama, kode, username…', 'Search name, code, username…')
add('customers.search_label', 'Cari pelanggan', 'Search customers')
add('customers.filter_router', 'Router', 'Router')
add('customers.filter_connection', 'Koneksi', 'Connection')
add('customers.filter_matches', 'hasil pencarian "{q}"', 'matching "{q}"')
add('customers.quick_tabs', 'Tab cepat', 'Quick tabs')
add('customers.tab_all', 'Semua', 'All')
add('customers.tab_incomplete', 'Data belum lengkap', 'Incomplete data')
add('customers.table_caption', 'Daftar layanan pelanggan', 'Customer service list')
add('customers.empty_title', 'Belum ada pelanggan', 'No customers yet')
add('customers.empty_desc', 'Tambahkan pelanggan pertama atau impor dari router/CSV.', 'Add your first customer or import from router/CSV.')
add('customers.empty_filtered_title', 'Tidak ada hasil untuk filter ini', 'No results for these filters')
add('customers.mapping_incomplete', 'pemetaan belum lengkap', 'mapping incomplete')
add('customers.col.customer', 'Pelanggan', 'Customer')
add('customers.col.username', 'Username', 'Username')
add('customers.col.service_kind', 'Layanan', 'Service')
add('customers.col.package', 'Paket', 'Plan')
add('customers.col.router', 'Router', 'Router')
add('customers.col.connection', 'Koneksi', 'Connection')
add('customers.col.job', 'Pekerjaan', 'Job')
add('customers.col.payment', 'Bayar', 'Payment')
add('customers.col.isolation', 'Isolir', 'Isolation')
add('customers.status.payment', 'Bayar', 'Payment')
add('customers.status.isolation', 'Isolir', 'Isolation')
add('customers.status.connection', 'Koneksi', 'Connection')
add('customers.status.job', 'Pekerjaan', 'Job')
add('customers.created_draft', 'Draft layanan tersimpan. Router tidak berubah.', 'Service draft saved. Router unchanged.')
add('customers.created_with_job', 'Pembuatan akun diterima sebagai pekerjaan. Pantau statusnya di pusat pekerjaan.', 'Account creation accepted as a job. Track its status in the job center.')
add('customers.detail_tabs', 'Detail layanan', 'Service detail')
add('customers.tab_summary', 'Ringkasan', 'Summary')
add('customers.tab_billing', 'Tagihan', 'Billing')
add('customers.tab_access', 'Akses', 'Access')
add('customers.tab_network', 'Jaringan', 'Network')
add('customers.tab_devices', 'Perangkat', 'Devices')
add('customers.tab_history', 'Riwayat', 'History')
add('customers.info_title', 'Informasi layanan', 'Service information')
add('customers.job_title', 'Pekerjaan aktif', 'Active job')
add('customers.job_none', 'Tidak ada pekerjaan berjalan untuk layanan ini.', 'No running job for this service.')
add('customers.open_jobs', 'Lihat pekerjaan', 'View jobs')
add('customers.f_name', 'Nama pelanggan', 'Customer name')
add('customers.f_label', 'Label layanan', 'Service label')
add('customers.f_label_helper', 'Opsional, mis. "Rumah" atau "Toko".', 'Optional, e.g. "Home" or "Shop".')
add('customers.f_router', 'Router pembatas', 'Restricting router')
add('customers.f_router_helper', 'Opsional; tanpa pembatasan akun berlaku pada semua router perusahaan.', 'Optional; unrestricted accounts apply to all company routers.')
add('customers.f_kind', 'Jenis layanan', 'Service type')
add('customers.f_package', 'Paket', 'Plan')
add('customers.f_package_helper', 'Paket komersial (harga/kecepatan); dapat dipetakan ke profile router.', 'Commercial plan (price/speed); can be mapped to a router profile.')
add('customers.f_start_date', 'Mulai layanan', 'Service start')
add('customers.f_contact', 'Kontak opsional', 'Contact (optional)')
add('customers.f_contact_helper', 'Telepon atau WhatsApp untuk keperluan operasional.', 'Phone or WhatsApp for operational use.')
add('customers.advanced_toggle', 'Bagian lanjutan', 'Advanced section')
add('customers.f_address', 'Alamat', 'Address')
add('customers.f_ip', 'IP statis', 'Static IP')
add('customers.f_ip_helper', 'Prefix wajib, contoh 192.0.2.2/24.', 'Prefix required, e.g. 192.0.2.2/24.')
add('customers.f_mac', 'MAC / serial perangkat', 'Device MAC / serial')
add('customers.f_odp', 'ODP', 'ODP')
add('customers.final_choice_label', 'Pilihan akhir', 'Final choice')
add('customers.final_choice_note', 'Router bersifat opsional; akun berlaku pada semua router perusahaan kecuali dibatasi.', 'Router is optional; accounts apply to all company routers unless restricted.')
add('customers.choice_draft', 'Simpan draft', 'Save draft')
add('customers.choice_draft_impact', 'Tidak mengubah router. Tidak memakai kuota.', 'Does not change the router. Does not use quota.')
add('customers.choice_draft_cta', 'Simpan draft', 'Save draft')
add('customers.choice_link_existing', 'Hubungkan akun existing', 'Link existing account')
add('customers.choice_link_existing_impact', 'Menyimpan pemetaan ke akun yang sudah ada. Tidak mengubah router. Memakai 1 kuota.', 'Stores a mapping to an existing account. Does not change the router. Uses 1 quota.')
add('customers.choice_link_existing_cta', 'Hubungkan akun', 'Link account')
add('customers.choice_create_account', 'Buat akun', 'Create account')
add('customers.choice_create_account_impact', 'Membuat akun pelanggan di basis RADIUS perusahaan. Tidak menulis ke router. Berlaku pada router yang sudah memakai RADIUS. Memakai 1 kuota.', 'Creates a customer account in the company RADIUS base. Does not write to the router. Applies to routers already using RADIUS. Uses 1 quota.')
add('customers.choice_create_account_cta', 'Buat akun', 'Create account')
add('customers.choice_create_and_activate', 'Buat dan aktifkan', 'Create and activate')
add('customers.choice_create_and_activate_impact', 'Membuat akun dan mengaktifkannya (berlaku pada router yang sudah memakai RADIUS).', 'Creates the account and activates it (applies to routers already using RADIUS).')
add('customers.choice_create_and_activate_cta', 'Buat dan aktifkan', 'Create and activate')
add('customers.access_all_routers', 'Semua router perusahaan', 'All company routers')
add('customers.access_none', 'Layanan ini belum memiliki akun akses.', 'This service has no access account yet.')
add('customers.access_state', 'Status akun', 'Account state')
add('customers.access_credential', 'Status kredensial', 'Credential state')
add('customers.access_session_limit', 'Batas sesi', 'Session limit')
add('customers.access_mac_lock', 'Kunci MAC', 'MAC lock')
add('customers.access_last_session', 'Sesi aktif terakhir', 'Last active session')
add('customers.access_restricting_router', 'Router pembatas', 'Restricting router')
add('customers.network_note', 'Koneksi ditentukan dari accounting RADIUS, bukan status pembayaran.', 'Connection is derived from RADIUS accounting, not payment status.')
add('customers.devices_none', 'Belum ada perangkat ACS yang terhubung dengan layanan ini.', 'No ACS devices linked to this service yet.')
add('customers.devices_r3_note', 'Manajemen perangkat (ACS) tersedia pada rilis R3.', 'Device management (ACS) arrives in the R3 release.')
add('customers.reveal_title', 'Tampilkan password', 'Show password')
add('customers.reveal_intent', 'Password hanya ditampilkan sekali dan disembunyikan otomatis.', 'The password is shown once and hidden automatically.')
add('customers.reveal_confirm', 'Tampilkan sekarang', 'Show now')
add('customers.reveal_password', 'Tampilkan password', 'Show password')
add('customers.reveal_note', 'Menampilkan ulang memerlukan konfirmasi identitas.', 'Re-displaying requires identity confirmation.')
add('customers.reveal_no_permission', 'Anda tidak memiliki izin untuk melihat password.', 'You do not have permission to view the password.')
add('customers.reveal_shown_once', 'Simpan sekarang; menampilkan ulang memerlukan konfirmasi identitas.', 'Save it now; re-displaying requires identity confirmation.')
add('customers.reveal_auto_hide', 'Sembunyi otomatis dalam {seconds} detik.', 'Auto-hides in {seconds} seconds.')

# ============ bulk ============
add('bulk.toolbar_label', 'Aksi massal', 'Bulk actions')
add('bulk.selected_on_page', '{count} layanan dipilih di halaman ini', '{count} service{count, plural, one {} other {s}} selected on this page')
add('bulk.select_all_results', 'Pilih seluruh hasil ({count})', 'Select all results ({count})')
add('bulk.clear_selection', 'Hapus pilihan', 'Clear selection')

# ============ freshness ============
add('freshness.updated', 'Data terakhir diperbarui {rel}', 'Last updated {rel}')
add('freshness.unknown', 'Waktu pembaruan tidak diketahui', 'Update time unknown')

# ============ audit ============
add('audit.empty', 'Belum ada aktivitas tercatat.', 'No recorded activity yet.')

# ============ jobs (U16) ============
add('jobs.title', 'Pusat Pekerjaan', 'Job Center')
add('jobs.desc', 'Seluruh pekerjaan lintas modul beserta status dan hasilnya.', 'All cross-module jobs with status and outcome.')
add('jobs.table_caption', 'Daftar pekerjaan', 'Job list')
add('jobs.col_kind', 'Jenis', 'Kind')
add('jobs.col_state', 'Status', 'Status')
add('jobs.col_router', 'Router', 'Router')
add('jobs.col_actor', 'Aktor', 'Actor')
add('jobs.col_created', 'Dibuat', 'Created')
add('jobs.col_updated', 'Diperbarui', 'Updated')
add('jobs.col_progress', 'Progres', 'Progress')
add('jobs.empty_title', 'Belum ada pekerjaan', 'No jobs yet')
add('jobs.empty_desc', 'Pekerjaan muncul saat aksi asynchronous dijalankan.', 'Jobs appear when asynchronous actions run.')
add('jobs.empty_router', 'Belum ada pekerjaan untuk router ini.', 'No jobs for this router yet.')
add('jobs.detail_title', 'Rincian pekerjaan', 'Job detail')
add('jobs.retry_cta', 'Coba lagi', 'Retry')
add('jobs.retry_submitted', 'Percobaan ulang dikirim sebagai pekerjaan baru', 'Retry submitted as a new job')
add('jobs.cancel_cta', 'Batalkan', 'Cancel')
add('jobs.cancel_confirm_title', 'Batalkan pekerjaan?', 'Cancel this job?')
add('jobs.cancel_confirm_intent', 'Pembatalan hanya berlaku bila belum ada efek yang terkirim.', 'Cancellation applies only when no effect has been sent.')
add('jobs.cancel_scope_note', 'Tahap yang masih berjalan akan dihentikan bila memungkinkan.', 'Running phases will be stopped where possible.')
add('jobs.cancel_reason_label', 'Alasan pembatalan', 'Cancellation reason')
add('jobs.cancel_reason_placeholder', 'mis. kebijakan berubah', 'e.g. policy changed')
add('jobs.cancel_default_reason', 'dibatalkan pengguna', 'cancelled by user')
add('jobs.cancel_done', 'Pekerjaan dibatalkan', 'Job cancelled')
add('jobs.uncertain_note', 'Hasil perubahan belum dapat dipastikan. Periksa hasil; jangan retry buta.', 'The change outcome cannot be confirmed yet. Inspect the result; do not retry blindly.')
add('jobs.recovery_note', 'Perlu pemulihan manual sebelum melanjutkan. Buka panduan pemulihan.', 'Manual recovery is needed before continuing. Open the recovery guide.')
add('jobs.leave_note', 'Meninggalkan halaman ini tidak menghentikan pekerjaan di server.', 'Leaving this page does not stop the job on the server.')
add('job.items_progress', '{done} dari {total} item selesai', '{done} of {total} items completed')
add('job.error_with_code', 'Gagal. Kode: {code} · request_id: {requestId}', 'Failed. Code: {code} · request_id: {requestId}')

for k, (a, b) in {
    'discover_router': ('Pindai router', 'Discover router'),
    'harvest_passwords': ('Panen password', 'Harvest passwords'),
    'commit_migration': ('Simpan migrasi', 'Commit migration'),
    'radius_cutover_step': ('Langkah cutover RADIUS', 'RADIUS cutover step'),
    'disconnect_session': ('Putus sesi', 'Disconnect session'),
    'apply_account_attributes': ('Terapkan atribut akun', 'Apply account attributes'),
    'suspend_service': ('Tangguhkan layanan', 'Suspend service'),
    'activate_service': ('Aktifkan layanan', 'Activate service'),
    'backup_router': ('Backup router', 'Back up router'),
    'import_commit': ('Simpan impor', 'Commit import'),
    'router_release': ('Lepas router', 'Release router'),
    'router_replace': ('Ganti router', 'Replace router'),
    'change_plan': ('Ubah paket', 'Change plan'),
}.items():
    add(f'job.kind.{k}', a, b)

for k, (a, b) in {
    'queued': ('Dalam antrean', 'Queued'),
    'connect': ('Menghubungkan', 'Connecting'),
    'read_sources': ('Membaca sumber', 'Reading sources'),
    'build_snapshot': ('Menyusun snapshot', 'Building snapshot'),
    'commit': ('Menyimpan', 'Committing'),
    'reserve': ('Mereservasi kuota', 'Reserving quota'),
    'create_account': ('Membuat akun', 'Creating account'),
    'verify': ('Memverifikasi', 'Verifying'),
    'transfer': ('Mentransfer', 'Transferring'),
    'export': ('Mengekspor', 'Exporting'),
    'temp_account': ('Akun sementara', 'Temporary account'),
    'read_creds': ('Membaca kredensial', 'Reading credentials'),
    'cleanup': ('Pembersihan', 'Cleanup'),
    'verify_cleanup': ('Verifikasi pembersihan', 'Verifying cleanup'),
    'fence': ('Menghentikan penulis', 'Fencing writer'),
    'detach': ('Melepas', 'Detaching'),
    'slot': ('Menyiapkan slot', 'Preparing slot'),
    'cutover_hint': ('Menyiapkan cutover', 'Preparing cutover'),
    'preflight': ('Pemeriksaan awal', 'Preflight'),
    'install_client': ('Memasang klien RADIUS', 'Installing RADIUS client'),
    'shadow': ('Mode bayangan', 'Shadow mode'),
    'authoritative': ('Mode otoritatif', 'Authoritative mode'),
    'apply': ('Menerapkan', 'Applying'),
    'disconnect': ('Memutus sesi', 'Disconnecting'),
}.items():
    add(f'enums.job_phase.{k}', a, b)

# ============ routers (U05/U06) ============
add('routers.list_title', 'Router', 'Routers')
add('routers.list_desc', 'Router MikroTik perusahaan Anda beserta status VPN, API, dan RADIUS.', 'Your company MikroTik routers with VPN, API, and RADIUS status.')
add('routers.table_caption', 'Daftar router', 'Router list')
add('routers.empty_title', 'Belum ada router', 'No routers yet')
add('routers.empty_desc', 'Hubungkan router MikroTik pertama Anda.', 'Connect your first MikroTik router.')
add('routers.col_router', 'Router', 'Router')
add('routers.col_health', 'Kesehatan', 'Health')
add('routers.col_mode', 'Mode', 'Mode')
add('routers.col_enforcement', 'Mode RADIUS', 'RADIUS mode')
add('routers.col_services', 'Layanan', 'Services')
add('routers.col_observed', 'Terpantau', 'Observed')
add('routers.new_title', 'Hubungkan router', 'Connect a router')
add('routers.new_desc', 'Daftarkan router dan jalankan skrip bootstrap aman di perangkat Anda.', 'Register the router and run the secure bootstrap script on your device.')
add('routers.wizard_steps', 'Langkah enrollment', 'Enrollment steps')
add('routers.step_identity', 'Identitas', 'Identity')
add('routers.step_prereq', 'Prasyarat', 'Prerequisites')
add('routers.step_script', 'Skrip', 'Script')
add('routers.step_waiting', 'Menunggu', 'Waiting')
add('routers.step_ready', 'Siap', 'Ready')
add('routers.f_display_name', 'Nama tampilan', 'Display name')
add('routers.f_router_code', 'Kode router', 'Router code')
add('routers.f_router_code_helper', '2–16 karakter: huruf besar, angka, tanda hubung.', '2–16 characters: uppercase letters, digits, hyphen.')
add('routers.f_location', 'Lokasi (opsional)', 'Location (optional)')
add('routers.f_mode', 'Mode pengelolaan', 'Management mode')
add('routers.mode_read_only', 'Hanya baca (default)', 'Read-only (default)')
add('routers.mode_read_only_hint', 'Pemindaian dan monitoring tanpa perubahan pada router.', 'Scanning and monitoring without changing the router.')
add('routers.mode_managed', 'Kelola', 'Managed')
add('routers.mode_managed_hint', 'Mengizinkan perubahan terverifikasi (mis. klien RADIUS saat cutover).', 'Allows verified changes (e.g. RADIUS client during cutover).')
add('routers.prereq_title', 'Prasyarat perangkat', 'Device prerequisites')
add('routers.prereq_v7', 'RouterOS v7 bila diketahui; versi lebih lama membatasi fitur.', 'RouterOS v7 where known; older versions limit features.')
add('routers.prereq_internet', 'Router memiliki akses internet aktif.', 'The router has active internet access.')
add('routers.prereq_terminal', 'Anda dapat membuka Terminal/router CLI.', 'You can open the Terminal/router CLI.')
add('routers.prereq_no_port', 'Tidak ada port Ethernet khusus yang diminta.', 'No specific Ethernet port is required.')
add('routers.script_title', 'Skrip bootstrap', 'Bootstrap script')
add('routers.script_purpose', 'Skrip ini melakukan hal berikut pada router Anda:', 'This script performs the following on your router:')
add('routers.copy_script', 'Salin skrip', 'Copy script')
add('routers.script_copied', 'Skrip disalin. Jalankan pada router tujuan setelah meninjau perubahan.', 'Script copied. Run it on the target router after reviewing the changes.')
add('routers.script_expires_note', 'Skrip kedaluwarsa dalam 15 menit.', 'The script expires in 15 minutes.')
add('routers.script_confidential', 'Jangan bagikan skrip ini — hanya untuk role berwenang.', 'Do not share this script — authorized roles only.')
add('routers.script_expired', 'Skrip kedaluwarsa. Token lama dicabut; buat ulang untuk melanjutkan.', 'The script expired. The old token is revoked; regenerate to continue.')
add('routers.script_regenerate', 'Buat ulang skrip', 'Regenerate script')
add('routers.script_waiting_cta', 'Saya telah menjalankan skrip', 'I have run the script')
add('routers.waiting_title', 'Menunggu verifikasi', 'Waiting for verification')
add('routers.waiting_desc', 'Handshake VPN → verifikasi API → autentikasi/izin → kompatibilitas. Tiap tahap punya hasil sendiri.', 'VPN handshake → API verification → authentication/permission → compatibility. Each stage has its own result.')
add('routers.waiting_note', 'Jangan tulis "router terhubung" sebelum handshake dan API terverifikasi.', 'The router is not "connected" until handshake and API are verified.')
add('routers.stage_vpn_handshake', 'Handshake VPN', 'VPN handshake')
add('routers.stage_api_verify', 'Verifikasi API', 'API verification')
add('routers.stage_auth_permission', 'Autentikasi dan izin', 'Authentication and permission')
add('routers.stage_compatibility', 'Kompatibilitas', 'Compatibility')
add('routers.ready_title', 'Router terverifikasi', 'Router verified')
add('routers.ready_desc', 'Handshake VPN dan API terverifikasi. Router siap dipakai — mulai dengan memindai akun existing.', 'VPN handshake and API are verified. The router is ready — start by scanning existing accounts.')
add('routers.cta_scan_accounts', 'Pindai akun existing', 'Scan existing accounts')
add('routers.cta_monitoring', 'Buka monitoring', 'Open monitoring')
add('routers.detail_tabs', 'Tab detail router', 'Router detail tabs')
add('routers.tab_summary', 'Ringkasan', 'Summary')
add('routers.tab_discovered', 'Akun ditemukan', 'Discovered accounts')
add('routers.tab_profiles', 'Profile', 'Profiles')
add('routers.tab_interfaces', 'Interface', 'Interfaces')
add('routers.tab_backup', 'Backup', 'Backups')
add('routers.tab_jobs', 'Pekerjaan', 'Jobs')
add('routers.tab_audit', 'Audit', 'Audit')
add('routers.info_title', 'Informasi router', 'Router information')
add('routers.identity_label', 'Identitas', 'Identity')
add('routers.serial_label', 'Nomor seri', 'Serial number')
add('routers.uptime_label', 'Waktu aktif', 'Uptime')
add('routers.cond_tunnel_down', 'Tunnel VPN terputus: manajemen tidak terjangkau. Ini bukan berarti internet pelanggan mati.', 'VPN tunnel is down: management unreachable. This does not mean customer internet is down.')
add('routers.cond_api_down', 'API tidak aktif atau izin kurang. Periksa konfigurasi API-SSL dan pengguna router.', 'API is down or permissions are insufficient. Check API-SSL configuration and the router user.')
add('routers.radius_panel_title', 'Panel RADIUS', 'RADIUS panel')
add('routers.radius_auth_ratio', 'Rasio autentikasi sukses (24 jam)', 'Auth success ratio (24h)')
add('routers.radius_sessions', 'Sesi masuk (24 jam)', 'Inbound sessions (24h)')
add('routers.radius_last_accounting', 'Accounting terakhir', 'Last accounting')
add('routers.radius_servers', 'Server RADIUS', 'RADIUS servers')
add('routers.radius_client_missing_client', 'Klien RADIUS belum terpasang di router ini.', 'The RADIUS client is not installed on this router.')
add('routers.radius_client_degraded', 'Klien RADIUS pada router tidak lengkap. Tinjau konfigurasi.', 'The RADIUS client on this router is incomplete. Review the configuration.')
add('routers.open_cutover', 'Buka cutover RADIUS', 'Open RADIUS cutover')
add('routers.capability_title', 'Kemampuan perangkat', 'Device capability')
add('routers.cap_pppoe', 'Layanan PPPoE', 'PPPoE service')
add('routers.cap_hotspot', 'Hotspot', 'Hotspot')
add('routers.cap_radius_client', 'Klien RADIUS', 'RADIUS client')
add('routers.cap_fasttrack_detect', 'Deteksi FastTrack', 'FastTrack detection')
add('routers.discovered_desc', 'Hasil pemindaian akun PPPoE/Hotspot pada router ini.', 'PPPoe/Hotspot account scan results for this router.')
add('routers.profiles_desc', 'Profile yang diamati pada router beserta pemetaan paket.', 'Profiles observed on the router along with plan mapping.')
add('routers.interfaces_hint', 'Data interface diperbarui berkala oleh kolektor monitoring.', 'Interface data is refreshed periodically by the monitoring collector.')
add('routers.interfaces_monitoring_note', 'Statistik per interface tersedia pada halaman monitoring.', 'Per-interface statistics are available on the monitoring page.')
add('routers.backup_count', '{count} artefak backup untuk router ini', '{count} backup artifact{count, plural, one {} other {s}} for this router')
add('routers.release_router', 'Lepas router', 'Release router')
add('routers.release_confirm_title', 'Lepas router {name}?', 'Release router {name}?')
add('routers.release_intent', 'Router diarsipkan dan slot kuotanya dibebaskan setelah penulis dihentikan dan NAS/peer ditangani.', 'The router is archived and its quota slot freed after the writer is fenced and NAS/peer handled.')
add('routers.release_scope_slot', 'Slot router dibebaskan setelah fencing selesai.', 'The router slot is freed after fencing completes.')
add('routers.release_scope_accounts', 'Akun RADIUS tetap milik perusahaan dan tidak terpengaruh.', 'RADIUS accounts remain company property and are unaffected.')
add('routers.release_scope_history', 'Histori lengkap tetap tersimpan.', 'Full history is retained.')
add('routers.release_submitted', 'Permintaan pelepasan diterima sebagai pekerjaan', 'Release request accepted as a job')
add('routers.replace_router', 'Ganti router', 'Replace router')
add('routers.replace_confirm_title', 'Ganti router {name}?', 'Replace router {name}?')
add('routers.replace_intent', 'Router baru memakai slot router lama selama masa tumpang tindih.', 'The new router uses the old router slot during the overlap window.')
add('routers.replace_scope_slot', 'Slot dipertukarkan; tidak dihitung ganda selama tumpang tindih maksimum 30 hari.', 'Slots are swapped; not double-counted during the 30-day maximum overlap.')
add('routers.replace_scope_accounts', 'Akun tidak diinput ulang — router baru hanya perlu enrollment dan cutover RADIUS.', 'Accounts are not re-entered — the new router only needs enrollment and RADIUS cutover.')
add('routers.replace_scope_overlap', 'Setelah 30 hari, tumpang tindih ditandai dan penambahan over-quota diblokir.', 'After 30 days the overlap is flagged and over-quota additions are blocked.')
add('routers.replace_submitted', 'Permintaan penggantian diterima', 'Replacement request accepted')

# ============ imports (U07/U08) ============
add('imports.title', 'Adopsi akun existing', 'Adopt existing accounts')
add('imports.desc', 'Migrasikan akun PPPoE/Hotspot dari router ke basis pengguna perusahaan — database-only, router tidak diubah.', 'Migrate PPPoE/Hotspot accounts from the router into the company user base — database-only, the router is untouched.')
add('imports.wizard_steps', 'Langkah migrasi', 'Migration steps')
add('imports.step_source', 'Sumber', 'Source')
add('imports.step_select', 'Pilih akun', 'Select accounts')
add('imports.step_identity', 'Gabungkan identitas', 'Merge identities')
add('imports.step_map_customers', 'Petakan pelanggan', 'Map customers')
add('imports.step_map_profiles', 'Petakan profile/paket', 'Map profiles/plans')
add('imports.step_password', 'Sumber password', 'Password source')
add('imports.step_review', 'Validasi dan tinjau', 'Validate and review')
add('imports.step_save', 'Simpan', 'Save')
add('imports.f_source_router', 'Router sumber', 'Source router')
add('imports.f_source_router_placeholder', 'Pilih router…', 'Choose a router…')
add('imports.f_source_helper', 'Pemindaian berjalan di latar belakang setelah dipilih.', 'Discovery runs in the background after selection.')
add('imports.fasttrack_warning', 'Aturan FastTrack dapat melewati antrean bandwidth. Aplikasi tidak mengubahnya; periksa pada router.', 'FastTrack rules may bypass bandwidth queues. The app does not change them; check on the router.')
add('imports.col_username', 'Username', 'Username')
add('imports.col_kind', 'Jenis', 'Kind')
add('imports.col_profile', 'Profile', 'Profile')
add('imports.col_service', 'Layanan', 'Service')
add('imports.col_state', 'Status', 'State')
add('imports.case_sensitive_note', 'perbedaan huruf besar/kecil', 'case-sensitive')
add('imports.no_accounts_title', 'Tidak ada akun ditemukan', 'No accounts found')
add('imports.no_accounts_desc', 'Pemindaian tidak menemukan akun PPPoE/Hotspot pada router ini.', 'The scan found no PPPoE/Hotspot accounts on this router.')
add('imports.select_desc', 'Pilih akun yang akan diadopsi. Akun yang dilewati tetap tidak berubah di router.', 'Choose accounts to adopt. Skipped accounts remain unchanged on the router.')
add('imports.identity_desc', 'Kandidat struktural ditampilkan dengan peringatan case-sensitive. Sesudah sumber credential tersedia, klasifikasi ulang dilakukan.', 'Structural candidates are shown with a case-sensitive warning. Re-classification happens once the credential source is available.')
add('imports.identity_no_conflicts', 'Tidak ada kandidat identitas ganda pada pemilihan ini.', 'No duplicate identity candidates in this selection.')
add('imports.conflict_kind_structural_match', 'kandidat struktural', 'structural match')
add('imports.conflict_kind_password_conflict', 'konflik password', 'password conflict')
add('imports.resolution_merge', 'Gabungkan', 'Merge')
add('imports.resolution_keep_one', 'Pilih satu', 'Keep one')
add('imports.resolution_rename', 'Rename', 'Rename')
add('imports.map_customers_desc', 'Petakan akun terpilih ke pelanggan yang sudah ada atau buat pelanggan baru.', 'Map selected accounts to existing customers or create new customers.')
add('imports.map_customers_note', 'Nama dan telepon bukan keunikan universal — keputusan tetap milik Anda.', 'Name and phone are not universal uniqueness — the decision stays with you.')
add('imports.map_profiles_desc', 'Pilih paket komersial untuk tiap kelompok profile router.', 'Pick a commercial plan for each router profile group.')
add('imports.map_profiles_note', 'Memilih profile tidak mengubah profile router; paket komersial (harga, kecepatan) diisi sekali per kelompok.', 'Selecting a profile does not change the router profile; commercial plan (price, speed) is filled once per group.')
add('imports.f_package_for_profile', 'Paket untuk profile ini', 'Plan for this profile')
add('imports.pkg_20m', 'Paket Rumah 20 Mbps', 'Home Plan 20 Mbps')
add('imports.pkg_50m', 'Paket Bisnis 50 Mbps', 'Business Plan 50 Mbps')
add('imports.pkg_10m', 'Paket Rumah 10 Mbps', 'Home Plan 10 Mbps')
add('imports.pkg_unmapped', 'Belum dipetakan', 'Unmapped')
add('imports.password_desc', 'Pilih sumber password. Tanpa credential, akun berstatus "password belum diketahui" dan tidak diaktifkan.', 'Choose the password source. Without credentials, accounts stay "password unknown" and are not activated.')
add('imports.pw_harvest_temporary', 'Panen sementara (S1)', 'Temporary harvest (S1)')
add('imports.pw_harvest_temporary_impact', 'Membuat akun migrasi sementara untuk membaca password; TTL maksimal 24 jam dengan pembersihan terverifikasi.', 'Creates a temporary migration account to read passwords; TTL max 24 hours with verified cleanup.')
add('imports.pw_harvest_ttl_note', 'Akun sementara kedaluwarsa maksimal 24 jam; pembersihan diverifikasi sebelum selesai.', 'The temporary account expires within 24 hours; cleanup is verified before completion.')
add('imports.pw_csv', 'CSV password', 'CSV passwords')
add('imports.pw_csv_impact', 'Password dibaca dari berkas CSV yang Anda unggah; cocok untuk data yang sudah Anda miliki.', 'Passwords are read from a CSV file you upload; suitable for data you already have.')
add('imports.pw_new_password', 'Password baru', 'New passwords')
add('imports.pw_new_password_impact', 'Password baru dibangkitkan; memerlukan pembaruan CPE (modem/router pelanggan).', 'New passwords are generated; requires CPE (customer modem/router) update.')
add('imports.pw_radius_import', 'Impor RADIUS eksternal (S4)', 'External RADIUS import (S4)')
add('imports.pw_radius_import_impact', 'Kredensial dibaca dari server RADIUS eksternal yang Anda tentukan.', 'Credentials are read from an external RADIUS server you designate.')
add('imports.pw_unknown', 'Password belum diketahui', 'Password unknown')
add('imports.pw_unknown_impact', 'Akun tidak dapat diaktifkan sampai sumber password dipilih.', 'Accounts cannot be activated until a password source is chosen.')
add('imports.pw_unknown_note', 'Password belum diketahui. Akun belum dapat diaktifkan.', 'Password unknown. Accounts cannot be activated yet.')
add('imports.harvest_started', 'Panen password dimulai sebagai pekerjaan latar belakang', 'Password harvest started as a background job')
add('imports.count_create', 'Akan dibuat', 'To create')
add('imports.count_merge', 'Akan digabung', 'To merge')
add('imports.count_conflicts', 'Konflik', 'Conflicts')
add('imports.count_quota', 'Kuota setelah simpan', 'Quota after save')
add('imports.save_cta', 'Simpan migrasi', 'Save migration')
add('imports.save_scope_accounts', '{count} akun disimpan ke basis pengguna', '{count} account{count, plural, one {} other {s}} saved to the user base')
add('imports.save_scope_router_unchanged', 'Router tidak diubah dan belum memakai RADIUS.', 'The router is unchanged and not yet using RADIUS.')
add('imports.save_scope_password', 'Sumber password: {source}', 'Password source: {source}')
add('imports.commit_title', 'Simpan migrasi?', 'Save this migration?')
add('imports.commit_intent', 'Akun tersimpan di basis pengguna perusahaan. Router belum diubah dan belum memakai RADIUS.', 'Accounts are saved to the company user base. The router is unchanged and not yet on RADIUS.')
add('imports.commit_scope_tenant', 'Berlaku untuk seluruh perusahaan Anda.', 'Applies to your entire company.')
add('imports.commit_scope_count', '{count} layanan dipilih untuk diadopsi.', '{count} service{count, plural, one {} other {s}} selected for adoption.')
add('imports.commit_scope_router_unchanged', 'Router tidak diubah; cutover RADIUS adalah langkah terpisah.', 'The router is unchanged; RADIUS cutover is a separate step.')
add('imports.commit_scope_billing', 'Tagihan dan isolir otomatis belum aktif.', 'Billing and automatic isolation are not active yet.')
add('imports.commit_accepted', 'Migrasi diterima sebagai pekerjaan', 'Migration accepted as a job')

# --- CSV ---
add('imports.csv_title', 'Impor CSV', 'CSV import')
add('imports.csv_desc', 'Lengkapi data pelanggan melalui CSV: unduh template, validasi, tinjau, lalu simpan.', 'Complete customer data via CSV: download the template, validate, review, then save.')
add('imports.csv_template_title', 'Templat CSV', 'CSV template')
add('imports.csv_template_desc', 'Batas berkas: {mb} MiB / {rows} baris. Kolom kosong mengikuti aturan mode. Berkas sama dapat diproses ulang.', 'File limits: {mb} MiB / {rows} rows. Empty columns follow mode rules. The same file can be reprocessed.')
add('imports.csv_download_template', 'Unduh templat', 'Download template')
add('imports.csv_mode_title', 'Mode impor', 'Import mode')
add('imports.csv_f_mode', 'Mode', 'Mode')
add('imports.csv_f_file', 'Berkas CSV', 'CSV file')
add('imports.csv_mode_create', 'Buat', 'Create')
add('imports.csv_mode_create_impact', 'Baris menjadi pelanggan/layanan baru.', 'Rows become new customers/services.')
add('imports.csv_mode_link', 'Hubungkan', 'Link')
add('imports.csv_mode_link_impact', 'Baris dipetakan ke akun existing tanpa mengubah router.', 'Rows map to existing accounts without touching the router.')
add('imports.csv_mode_update', 'Perbarui', 'Update')
add('imports.csv_mode_update_impact', 'Baris memperbarui data pelanggan/layanan existing.', 'Rows update existing customer/service data.')
add('imports.csv_mode_device_mapping', 'Pemetaan perangkat', 'Device mapping')
add('imports.csv_mode_device_mapping_impact', 'Baris memetakan perangkat ke layanan.', 'Rows map devices to services.')
add('imports.csv_mode_password_migration', 'Migrasi password', 'Password migration')
add('imports.csv_mode_password_migration_impact', 'Baris menyediakan password untuk akun yang sudah ada.', 'Rows provide passwords for existing accounts.')
add('imports.csv_upload_title', 'Unggah berkas', 'Upload file')
add('imports.csv_pick_file', 'Pilih berkas CSV', 'Choose CSV file')
add('imports.csv_validate_cta', 'Validasi berkas', 'Validate file')
add('imports.csv_too_large', 'Berkas melebihi batas {mb} MiB.', 'File exceeds the {mb} MiB limit.')
add('imports.csv_too_many_rows', 'Berkas melebihi batas {count} baris.', 'File exceeds the {count}-row limit.')
add('imports.csv_result_title', 'Hasil validasi', 'Validation result')
add('imports.csv_total_rows', 'Total baris', 'Total rows')
add('imports.csv_valid_rows', 'Baris valid', 'Valid rows')
add('imports.csv_error_rows', 'Baris bermasalah', 'Problem rows')
add('imports.csv_errors_desc', 'Perbaiki baris berikut — baris, field, alasan, dan tindakan:', 'Fix the following rows — row, field, reason, and action:')
add('imports.csv_err_row', 'Baris', 'Row')
add('imports.csv_err_field', 'Field', 'Field')
add('imports.csv_err_reason', 'Alasan', 'Reason')
add('imports.csv_err_action', 'Tindakan', 'Action')
add('imports.csv_retry_note', 'File sama dapat diproses ulang; retry tidak menduplikasi baris yang tersimpan.', 'The same file can be reprocessed; retry does not duplicate saved rows.')
add('imports.csv_all_invalid_title', 'Tidak ada baris valid', 'No valid rows')
add('imports.csv_all_invalid_desc', 'Perbaiki baris bermasalah lalu unggah ulang berkas yang sama.', 'Fix the problem rows then re-upload the same file.')
add('imports.csv_commit_cta', 'Simpan {count} baris valid', 'Save {count} valid row{count, plural, one {} other {s}}')
add('imports.csv_committed', 'Impor diterima: {count} baris sedang diproses', 'Import accepted: {count} row{count, plural, one {} other {s}} processing')
add('imports.csv_commit_title', 'Simpan impor CSV?', 'Save this CSV import?')
add('imports.csv_commit_intent', '{count} baris valid akan disimpan sebagai pekerjaan.', '{count} valid row{count, plural, one {} other {s}} will be saved as a job.')
add('imports.csv_commit_scope_mode', 'Mode: {mode}.', 'Mode: {mode}.')
add('imports.csv_commit_scope_empty_note', 'Baris kosong tidak menghapus data apa pun.', 'Empty rows do not delete any data.')

# ============ monitoring (U13) ============
add('monitoring.title', 'Monitoring', 'Monitoring')
add('monitoring.desc', 'Kesehatan router, interface, dan status RADIUS — dengan waktu pengamatan dan sumber.', 'Router health, interfaces, and RADIUS status — with observation time and source.')
add('monitoring.group_tabs', 'Kelompok status', 'Status groups')
add('monitoring.group_all', 'Semua', 'All')
add('monitoring.group_healthy', 'Sehat', 'Healthy')
add('monitoring.group_disturbed', 'Terganggu', 'Disturbed')
add('monitoring.group_unmonitored', 'Tidak terpantau', 'Unmonitored')
add('monitoring.group_stale_data', 'Data usang', 'Stale data')
add('monitoring.group_management_unreachable', 'Manajemen tidak terjangkau', 'Management unreachable')
add('monitoring.group_empty', 'Tidak ada router pada kelompok ini.', 'No routers in this group.')
add('monitoring.management_note', 'VPN aktif dengan API gagal berarti kondisi manajemen — bukan berarti internet pelanggan mati.', 'VPN up with API down is a management condition — not necessarily customer internet down.')
add('monitoring.stale_note', 'Data usang: pemantauan tidak tersedia untuk sebagian router. Kolektor gagal bukan router mati.', 'Stale data: monitoring unavailable for some routers. Collector failure does not mean routers are down.')
add('monitoring.interfaces_title', 'Interface', 'Interfaces')
add('monitoring.radius_title', 'RADIUS', 'RADIUS')
add('monitoring.radius_auth_ratio', 'Rasio autentikasi sukses (24 jam)', 'Auth success ratio (24h)')
add('monitoring.radius_sessions', 'Sesi masuk (24 jam)', 'Inbound sessions (24h)')
add('monitoring.radius_last_accounting', 'Accounting terakhir', 'Last accounting')
add('monitoring.radius_no_data', 'Data RADIUS tidak tersedia untuk router ini.', 'RADIUS data unavailable for this router.')
add('monitoring.traffic_caption', 'Trafik WAN', 'WAN traffic')

# ============ backups (U12) ============
add('backups.title', 'Backup', 'Backups')
add('backups.desc', 'Jadwal, histori, retensi, dan unduhan artefak per router.', 'Schedules, history, retention, and artifact downloads per router.')
add('backups.schedule_title', 'Jadwal', 'Schedule')
add('backups.schedule_empty', 'Belum ada jadwal backup terdaftar.', 'No backup schedule registered yet.')
add('backups.freq_daily', 'harian', 'daily')
add('backups.freq_weekly', 'mingguan', 'weekly')
add('backups.type_binary', 'artefak biner', 'binary artifact')
add('backups.type_export', 'ekspor konfigurasi', 'configuration export')
add('backups.notif_on', 'notifikasi aktif', 'notifications on')
add('backups.retention_title', 'Retensi', 'Retention')
add('backups.retention_routine', 'Generasi rutin', 'Routine generations')
add('backups.retention_manual', 'Backup manual', 'Manual backups')
add('backups.retention_prechange', 'Backup pra-perubahan', 'Pre-change backups')
add('backups.retention_note', '100 generasi rutin terakhir per router; manual dan pra-perubahan masing-masing 10, ditampilkan terpisah.', 'Last 100 routine generations per router; manual and pre-change 10 each, shown separately.')
add('backups.recovery_key_title', 'Kunci pemulihan', 'Recovery key')
add('backups.recovery_key_desc', 'Kunci enkripsi backup. Tampilkan hanya bila diperlukan.', 'The backup encryption key. Reveal only when needed.')
add('backups.show_key', 'Tampilkan kunci', 'Show key')
add('backups.recovery_key_reauth', 'Menampilkan kunci memerlukan reautentikasi + MFA.', 'Showing the key requires reauthentication + MFA.')
add('backups.run_now', 'Backup sekarang', 'Back up now')
add('backups.run_confirm_title', 'Jalankan backup sekarang?', 'Run a backup now?')
add('backups.run_confirm_intent', 'Backup akan dibuat untuk router terjadwal dan ditransfer terenkripsi.', 'A backup will be created for the scheduled router and transferred encrypted.')
add('backups.run_scope_router', 'Backup berjalan per router.', 'Backups run per router.')
add('backups.run_scope_note', 'Kegagalan transfer tidak menghapus backup lama.', 'Transfer failure does not delete old backups.')
add('backups.run_submitted', 'Backup dikirim sebagai pekerjaan', 'Backup submitted as a job')
add('backups.history_title', 'Histori', 'History')
add('backups.col_generation', 'Generasi', 'Generation')
add('backups.col_router', 'Router', 'Router')
add('backups.col_created', 'Waktu', 'Time')
add('backups.col_category', 'Kategori', 'Category')
add('backups.col_size', 'Ukuran', 'Size')
add('backups.col_transfer', 'Hasil transfer', 'Transfer result')
add('backups.col_encrypted', 'Enkripsi', 'Encrypted')
add('backups.empty_title', 'Belum ada backup', 'No backups yet')
add('backups.empty_desc', 'Backup muncul setelah jadwal berjalan atau backup manual.', 'Backups appear after a schedule runs or a manual backup.')
add('backups.download_cta', 'Unduh', 'Download')
add('backups.download_reauth_note', 'Unduhan memerlukan izin, reautentikasi/kunci pemulihan; tautan berlaku 5 menit.', 'Download requires permission, reauthentication/recovery key; the link is valid for 5 minutes.')
add('backups.staging_note', 'Staging dan pembersihan tidak dihitung sebagai backup siap unduh.', 'Staging and cleanup are not counted as downloadable backups.')
add('backups.restore_title', 'Restore', 'Restore')
add('backups.restore_desc', 'Restore adalah menu berisiko terpisah dan hanya tersedia bila versi/topologi didukung (melalui runbook lab).', 'Restore is a separate high-risk menu, available only when version/topology are supported (via the lab runbook).')

# ============ radius (U19) ============
add('radius.title', 'Basis Akun RADIUS', 'RADIUS Account Base')
add('radius.desc', 'Akun akses perusahaan, status per router, dan cutover RADIUS.', 'Company access accounts, per-router status, and RADIUS cutover.')
add('radius.tabs_label', 'Area RADIUS', 'RADIUS areas')
add('radius.tab_accounts', 'Akun', 'Accounts')
add('radius.tab_routers', 'Router', 'Routers')
add('radius.tab_cutover', 'Cutover', 'Cutover')
add('radius.table_caption', 'Daftar akun akses RADIUS', 'RADIUS access account list')
add('radius.search_placeholder', 'Cari username…', 'Search username…')
add('radius.search_label', 'Cari akun', 'Search accounts')
add('radius.password_never_shown', 'Password tidak pernah tampil di tabel.', 'Passwords never appear in tables.')
add('radius.col_username', 'Username', 'Username')
add('radius.col_kind', 'Jenis', 'Kind')
add('radius.col_state', 'Status', 'State')
add('radius.col_credential', 'Kredensial', 'Credential')
add('radius.col_restriction', 'Router pembatas', 'Restricting router')
add('radius.col_last_session', 'Sesi terakhir', 'Last session')
add('radius.empty_accounts_title', 'Belum ada akun RADIUS', 'No RADIUS accounts yet')
add('radius.empty_accounts_desc', 'Akun muncul setelah adopsi/migrasi atau pembuatan akun.', 'Accounts appear after adoption/migration or account creation.')
add('radius.migrated_accounts', 'Akun dimigrasikan', 'Migrated accounts')
add('radius.auth_ratio_24h', 'Rasio autentikasi sukses (24 jam)', 'Auth success ratio (24h)')
add('radius.sessions_24h', 'Sesi masuk (24 jam)', 'Inbound sessions (24h)')
add('radius.last_accounting', 'Accounting terakhir', 'Last accounting')
add('radius.servers', 'Server RADIUS', 'RADIUS servers')
add('radius.client_status', 'Status klien', 'Client status')
add('radius.open_cutover_cta', 'Lanjutkan ke cutover', 'Continue to cutover')
add('radius.cutover_permission_note', 'Cutover memerlukan izin radius.cutover + MFA + reautentikasi.', 'Cutover requires radius.cutover permission + MFA + reauthentication.')
add('radius.cutover_intro', 'Cutover mengubah router untuk memakai basis pengguna perusahaan. Tidak ada janji nol downtime universal; tiap langkah punya exit criterion.', 'Cutover switches the router to the company user base. No universal zero-downtime promise; each step has exit criteria.')
add('radius.cutover_b0_title', 'B0 — Rencana & pra-pemeriksaan', 'B0 — Plan & preflight')
add('radius.cutover_b0_desc', 'Backup router dan verifikasi prasyarat sebelum perubahan apa pun.', 'Back up the router and verify prerequisites before any change.')
add('radius.cutover_b1_title', 'B1 — Paritas data', 'B1 — Data parity')
add('radius.cutover_b1_desc', 'Bandingkan akun router dengan basis pengguna perusahaan.', 'Compare router accounts against the company user base.')
add('radius.cutover_b2_title', 'B2 — Pemasangan klien', 'B2 — Client installation')
add('radius.cutover_b2_desc', 'Pasang klien RADIUS primer/sekunder pada router.', 'Install primary/secondary RADIUS clients on the router.')
add('radius.cutover_b3_title', 'B3 — Mode bayangan', 'B3 — Shadow mode')
add('radius.cutover_b3_desc', 'Autentikasi dicatat dari RADIUS tanpa mengubah akun lokal; observasi minimal 30 menit.', 'Authentication is recorded from RADIUS without changing local accounts; minimum 30 minutes of observation.')
add('radius.cutover_b4_title', 'B4 — Kanari', 'B4 — Canary')
add('radius.cutover_b4_desc', 'Uji kelompok kecil akun di mode otoritatif; observasi minimal 24 jam.', 'Test a small account group in authoritative mode; minimum 24 hours of observation.')
add('radius.cutover_b5_title', 'B5 — Aktif penuh', 'B5 — Full activation')
add('radius.cutover_b5_desc', 'Aktifkan otoritatif per batch (maksimal 100 akun) dengan metode teruji; reautentikasi dan izin deletion eksplisit bila dipilih.', 'Activate authoritative per batch (max 100 accounts) with a tested method; reauthentication and explicit deletion permission when chosen.')
add('radius.cutover_b6_title', 'B6 — Otoritatif penuh', 'B6 — Fully authoritative')
add('radius.cutover_b6_desc', 'Router sepenuhnya memakai basis pengguna perusahaan; akun lokal dapat dibersihkan terjadwal.', 'The router fully uses the company user base; local accounts can be cleaned on schedule.')
add('radius.cutover_exit_note', 'Tombol lanjut aktif hanya bila exit criterion terpenuhi; hasil ambigu berstatus uncertain/recovery_required tanpa "ulangi semua".', 'Continue is enabled only when exit criteria are met; ambiguous outcomes become uncertain/recovery_required with no "retry everything".')
add('radius.rollback_note', 'Rollback menjelaskan pemulihan snapshot/revision yang sah dan hold yang dipertahankan; coverage recovery tidak lengkap menjadi recovery_required.', 'Rollback explains valid snapshot/revision recovery and retained holds; incomplete recovery coverage becomes recovery_required.')
add('radius.start_cutover', 'Mulai cutover', 'Start cutover')
add('radius.cutover_confirm_title', 'Mulai cutover router {name}?', 'Start cutover for router {name}?')
add('radius.cutover_confirm_intent', 'Router akan diarahkan memakai basis pengguna perusahaan langkah demi langkah.', 'The router will be switched to the company user base step by step.')
add('radius.cutover_scope_settings', 'Shared setting dan ownership ditampilkan sebelum tiap langkah.', 'Shared settings and ownership are shown before each step.')
add('radius.cutover_scope_accounts', '{count} akun terdampak pada router ini.', '{count} account{count, plural, one {} other {s}} affected on this router.')
add('radius.cutover_scope_batches', 'Aktif penuh berjalan per batch maksimal 100 akun.', 'Full activation runs in batches of at most 100 accounts.')
add('radius.cutover_scope_rollback', 'Rollback tersedia dengan pemulihan snapshot yang sah.', 'Rollback is available with valid snapshot recovery.')
add('radius.cutover_started', 'Cutover dimulai sebagai pekerjaan', 'Cutover started as a job')

# ============ packages ============
add('packages.title', 'Paket dan Profile', 'Plans and Profiles')
add('packages.desc', 'Paket komersial perusahaan dan pemetaannya ke profile router.', 'Company commercial plans and their mapping to router profiles.')
add('packages.binding_note', 'Pemetaan paket→profile per router (binding) beserta fingerprint versi. Profile yang diamati tidak diubah otomatis.', 'Plan→profile mapping per router (binding) with version fingerprints. Observed profiles are not changed automatically.')
add('packages.col_package', 'Paket', 'Plan')
add('packages.col_restriction', 'Pembatasan', 'Restriction')
add('packages.accounts_count', 'akun', 'accounts')
add('packages.write_note', 'Penulisan binding memerlukan izin profiles.write; kontrak API binding ditetapkan pada TK-408.', 'Writing bindings requires profiles.write permission; the binding API contract is set in TK-408.')
add('packages.empty_title', 'Belum ada paket', 'No plans yet')
add('packages.empty_desc', 'Paket muncul setelah adopsi atau pembuatan layanan.', 'Plans appear after adoption or service creation.')
add('packages.table_caption', 'Akun per paket', 'Accounts per plan')

# ============ settings (U18) ============
add('settings.title', 'Pengaturan', 'Settings')
add('settings.desc', 'Pengaturan perusahaan {tenant}.', 'Settings for {tenant}.')
add('settings.language_title', 'Bahasa', 'Language')
add('settings.language_desc', 'Bahasa tampilan Anda. Pemilihan bahasa tidak menghapus isian formulir.', 'Your display language. Changing language does not clear form input.')
add('settings.open_audit', 'Buka jejak audit', 'Open audit trail')
add('settings.audit_title', 'Jejak audit', 'Audit trail')
add('settings.audit_desc', 'Aktivitas sensitif tercatat dengan aktor dan waktu.', 'Sensitive activity is recorded with actor and time.')
add('settings.support_title', 'Akses dukungan', 'Support access')
add('settings.support_desc', 'Bila diperlukan, Owner dapat memberi akses dukungan berscope dan berbatas waktu.', 'If needed, the Owner can grant scoped, time-limited support access.')
add('settings.support_note', 'SupportGrant selalu menampilkan banner selama sesi dukungan aktif dan dapat diakhiri kapan saja.', 'A SupportGrant always shows a banner during the session and can be ended at any time.')
add('settings.team_title', 'Perusahaan dan Tim', 'Company and Team')
add('settings.team_desc', 'Anggota tim {tenant} beserta peran dan status MFA.', 'Members of {tenant} with roles and MFA status.')
add('settings.team_col_name', 'Anggota', 'Member')
add('settings.team_col_role', 'Peran', 'Role')
add('settings.team_col_mfa', 'MFA', 'MFA')
add('settings.mfa_on', 'aktif', 'enabled')
add('settings.mfa_off', 'belum aktif', 'not enabled')
add('settings.tenant_language_title', 'Bahasa default perusahaan', 'Company default language')
add('settings.tenant_language_desc', 'Bahasa default untuk operator baru dan dokumen terbitan perusahaan.', 'Default language for new operators and company-issued documents.')
add('settings.invite_title', 'Undang anggota', 'Invite member')
add('settings.invite_desc', 'Undangan dikirim via email dengan peran yang Anda pilih.', 'Invitations are sent via email with the role you choose.')
add('settings.invite_cta', 'Undang', 'Invite')
add('settings.invite_blocked_note', 'endpoint undangan tim belum tersedia pada adapter pengembangan', 'the team invitation endpoint is not yet available in the dev adapter')
add('settings.subscription_title', 'Paket Aplikasi', 'Application Plan')
add('settings.subscription_desc', 'Paket aktif, periode, pemakaian, dan perubahan paket.', 'Active plan, period, usage, and plan changes.')
add('settings.subscription_view_only', 'Hanya tampilan — perubahan paket memerlukan izin subscription.manage.', 'View only — plan changes require subscription.manage permission.')
add('settings.sub_plan', 'Paket aktif', 'Active plan')
add('settings.sub_no_period', 'tanpa periode berbayar', 'no paid period')
add('settings.sub_routers_used', 'Router terpakai', 'Routers used')
add('settings.sub_services_used', 'Layanan terpakai', 'Services used')
add('settings.sub_drafts_used', 'Draft tersimpan', 'Drafts stored')
add('settings.sub_drafts_hint', 'Draft manual tidak memakai kuota layanan.', 'Manual drafts do not consume service quota.')
add('settings.sub_quota_label', 'Penggunaan kuota layanan', 'Service quota usage')
add('settings.sub_quota_note', '{used} dari {limit} layanan terpakai.', '{used} of {limit} services used.')
add('settings.sub_state_free', 'Paket gratis.', 'Free plan.')
add('settings.sub_state_active', 'Langganan aktif.', 'Subscription active.')
add('settings.sub_state_pending', 'Menunggu pembayaran/persetujuan.', 'Awaiting payment/approval.')
add('settings.sub_state_grace', 'Masa tenggang 7 hari. Perpanjang untuk menghindari pembatasan.', 'Grace period: 7 days. Renew to avoid restrictions.')
add('settings.sub_state_restricted', 'Penambahan router/layanan baru dibatasi. Layanan pelanggan Anda tetap berjalan.', 'Adding new routers/services is limited. Your customer services keep running.')
add('settings.sub_state_ended', 'Read-only + pembayaran + export. Autentikasi RADIUS pelanggan tetap dilayani selama masa retensi.', 'Read-only + payment + export. Customer RADIUS authentication is still served during retention.')
add('settings.sub_pending_invoice', 'Invoice tertunda', 'Pending invoice')
add('settings.sub_due', 'jatuh tempo {date}', 'due {date}')
add('settings.upload_proof_cta', 'Unggah bukti pembayaran', 'Upload payment proof')
add('settings.upload_blocked_note', 'unggahan bukti menunggu endpoint payment-submissions aktif pada adapter pengembangan', 'proof upload awaits the payment-submissions endpoint in the dev adapter')
add('settings.change_plan_title', 'Ubah paket', 'Change plan')
add('settings.request_upgrade', 'Minta penawaran', 'Request quotation')
add('settings.upgrade_note', 'Upgrade: periode baru mulai hari persetujuan; sisa hari ditambahkan sebagai hari bonus.', 'Upgrade: the new period starts on approval day; remaining days are added as bonus days.')
add('settings.downgrade_note', 'Downgrade berlaku saat perpanjangan dan ditolak bila pemakaian melebihi batas paket tujuan.', 'Downgrade applies at renewal and is rejected if usage exceeds the target plan limit.')
add('settings.quotation_title', 'Minta penawaran?', 'Request a quotation?')
add('settings.quotation_intent', 'Penawaran untuk paket {plan} akan diterbitkan beserta invoice.', 'A quotation for the {plan} plan will be issued along with an invoice.')
add('settings.quotation_scope_period', 'Periode baru dimulai pada tanggal persetujuan.', 'The new period starts on the approval date.')
add('settings.quotation_scope_bonus', 'Sisa hari periode lama ditambahkan sebagai hari bonus.', 'Remaining old-period days are added as bonus days.')
add('settings.quotation_scope_invoice', 'Instruksi pembayaran tampil pada invoice terautentikasi.', 'Payment instructions appear on the authenticated invoice.')
add('settings.quotation_confirm', 'Terbitkan penawaran', 'Issue quotation')
add('settings.quotation_created', 'Penawaran diterbitkan: {amount}', 'Quotation issued: {amount}')
add('settings.last_activity', 'Aktivitas terakhir: {time}', 'Last activity: {time}')

# ============ admin (U14) ============
add('admin.workspace_label', 'ADMIN PLATFORM', 'PLATFORM ADMIN')
add('admin.title', 'Approval Langganan', 'Subscription Approvals')
add('admin.desc', 'Antrean verifikasi pembayaran aplikasi lintas perusahaan.', 'Cross-company application payment verification queue.')
add('admin.back_to_tenant', 'Kembali ke ruang tenant', 'Back to tenant workspace')
add('admin.queue_tabs', 'Antrean', 'Queues')
add('admin.queue_submitted', 'Menunggu verifikasi', 'Awaiting verification')
add('admin.queue_revision', 'Perlu perbaikan', 'Needs revision')
add('admin.queue_approved', 'Disetujui', 'Approved')
add('admin.queue_rejected', 'Ditolak', 'Rejected')
add('admin.table_caption', 'Daftar pengajuan pembayaran', 'Payment submission list')
add('admin.empty_queue', 'Antrean kosong.', 'Queue is empty.')
add('admin.col_tenant', 'Perusahaan', 'Company')
add('admin.col_plan', 'Paket/periode', 'Plan/term')
add('admin.col_amount', 'Nominal', 'Amount')
add('admin.col_submitted', 'Waktu submit', 'Submitted')
add('admin.col_state', 'Status', 'Status')
add('admin.months', 'bulan', 'months')
add('admin.assignee', 'Petugas', 'Assignee')
add('admin.detail_title', 'Rincian & keputusan', 'Detail & decision')
add('admin.detail_empty', 'Pilih baris untuk melihat bukti, data transfer, dan invoice.', 'Select a row to view proof, transfer data, and the invoice.')
add('admin.proof_title', 'Bukti pembayaran', 'Payment proof')
add('admin.proof_note', 'Gambar bukti bukan hasil pencocokan bank. Periksa rekening, tanggal, jumlah, dan referensi.', 'A proof image is not a bank match. Check the account, date, amount, and reference.')
add('admin.proof_scanning', 'Bukti sedang diperiksa (pemindaian keamanan); dapat dilihat setelah lolos.', 'Proof is being scanned (security); viewable after it passes.')
add('admin.view_proof', 'Lihat bukti', 'View proof')
add('admin.approve_cta', 'Setujui', 'Approve')
add('admin.approve_title', 'Setujui pembayaran?', 'Approve this payment?')
add('admin.approve_intent', 'Dana {amount} dari {tenant} akan dikonfirmasi dan hak paket diterapkan.', 'The {amount} from {tenant} will be confirmed and entitlements applied.')
add('admin.approve_scope_funds', 'Konfirmasi ini menyatakan "Dana telah diterima di rekening".', 'This confirmation states "Funds have been received in the account".')
add('admin.approve_scope_entitlement', 'Perubahan hak paket diterapkan atomik.', 'Plan entitlement changes are applied atomically.')
add('admin.approved_toast', 'Pembayaran disetujui', 'Payment approved')
add('admin.reject_cta', 'Tolak', 'Reject')
add('admin.reject_title', 'Tolak pembayaran?', 'Reject this payment?')
add('admin.reject_intent', 'Pengajuan ditolak dengan alasan yang dikirim ke perusahaan.', 'The submission is rejected with a reason sent to the company.')
add('admin.rejected_toast', 'Pengajuan ditolak', 'Submission rejected')
add('admin.request_revision_cta', 'Minta perbaikan', 'Request revision')
add('admin.revision_title', 'Minta perbaikan bukti?', 'Request proof revision?')
add('admin.revision_intent', 'Perusahaan akan diminta memperbaiki bukti sebelum keputusan akhir.', 'The company will be asked to fix the proof before a final decision.')
add('admin.revision_toast', 'Permintaan perbaikan dikirim', 'Revision requested')
add('admin.reason_label', 'Alasan', 'Reason')
add('admin.reason_required_note', 'Alasan wajib diisi untuk keputusan ini.', 'A reason is required for this decision.')
add('admin.decision_done_note', 'Keputusan sudah dibuat untuk berkas ini.', 'A decision has already been made for this file.')
add('admin.privacy_note', 'Ruang admin hanya menampilkan usage, health VPN/API, outcome job/backup, dan paket — tanpa drill-down PII/ledger/rahasia.', 'The admin workspace shows only usage, VPN/API health, job/backup outcomes, and plans — no PII/ledger/secret drill-down.')

# ============ validation ============
add('validation.required', 'Wajib diisi', 'Required')
add('validation.email_invalid', 'Format email tidak valid', 'Invalid email format')
add('validation.password_min', 'Password minimal {count} karakter', 'Password must be at least {count} characters')
add('validation.totp_digits', 'Kode TOTP harus 6 digit', 'TOTP code must be 6 digits')
add('validation.router_code', 'Kode router 2–16 karakter: huruf besar, angka, tanda hubung', 'Router code: 2–16 characters, uppercase letters, digits, hyphen')
add('validation.ip_prefix', 'IP harus menyertakan prefix, mis. 192.0.2.2/24', 'IP must include a prefix, e.g. 192.0.2.2/24')
add('validation.summary', 'Periksa kembali isian yang ditandai.', 'Please review the highlighted fields.')
for code, (a, b) in {
    'required': ('Kolom wajib diisi', 'Field is required'),
    'email': ('Format email tidak valid', 'Invalid email format'),
    'min_length': ('Nilai terlalu pendek', 'Value too short'),
    'pattern': ('Format tidak sesuai', 'Format mismatch'),
    'max_rows': ('Melebihi batas baris', 'Exceeds row limit'),
    'max_size': ('Melebihi batas ukuran', 'Exceeds size limit'),
    'mime': ('Jenis berkas tidak didukung', 'Unsupported file type'),
    'ip_prefix': ('IP harus dengan prefix', 'IP must have a prefix'),
}.items():
    add(f'validation.csv_{code}', a, b)

# ============ chart ============
add('chart.unit_bits', 'bit/detik', 'bits per second')
add('chart.range', 'Rentang waktu', 'Time range')
add('chart.range_24h', '24 jam', '24 hours')
add('chart.range_7d', '7 hari', '7 days')
add('chart.show_table', 'Lihat sebagai tabel', 'View as table')
add('chart.col_time', 'Waktu', 'Time')
add('chart.col_value', 'Nilai', 'Value')
add('chart.gap_note', 'Grafik memuat gap: data tidak tersedia tetap ditampilkan sebagai gap, bukan nol.', 'The chart contains gaps: unavailable data is shown as gaps, not zeros.')
add('chart.has_gaps', 'memuat gap data', 'contains data gaps')
add('chart.max_value', 'Nilai tertinggi {value}', 'Peak value {value}')

# ============ enums ============
for v, (a, b) in {
    'online': ('Online', 'Online'), 'offline': ('Offline', 'Offline'), 'unknown': ('Tidak diketahui', 'Unknown'),
}.items():
    add(f'enums.connection.{v}', a, b)
for v, (a, b) in {
    'normal': ('Normal', 'Normal'), 'isolated': ('Terisolir', 'Isolated'),
    'awaiting_verification': ('Menunggu verifikasi', 'Awaiting verification'), 'hold': ('Hold', 'Hold'),
}.items():
    add(f'enums.isolation.{v}', a, b)
for v, (a, b) in {
    'unbilled': ('Belum dibayar', 'Unpaid'), 'partial': ('Sebagian', 'Partial'),
    'paid': ('Lunas', 'Paid'), 'not_billed': ('Tidak ditagih', 'Not billed'),
}.items():
    add(f'enums.payment.{v}', a, b)
for v, (a, b) in {
    'none': ('Tidak ada', 'None'), 'queued': ('Antre', 'Queued'),
    'running': ('Berjalan', 'Running'), 'needs_review': ('Perlu ditinjau', 'Needs review'),
}.items():
    add(f'enums.job_dimension.{v}', a, b)
for v, (a, b) in {
    'draft': ('Draft', 'Draft'), 'pending': ('Menunggu', 'Pending'), 'provisioning': ('Menyiapkan', 'Provisioning'),
    'provisioned': ('Aktif', 'Provisioned'), 'conflict': ('Konflik', 'Conflict'), 'failed': ('Gagal', 'Failed'),
    'terminated': ('Dihentikan', 'Terminated'), 'archived': ('Diarsipkan', 'Archived'),
}.items():
    add(f'enums.lifecycle.{v}', a, b)
for v, (a, b) in {
    'local': ('Lokal', 'Local'), 'radius_shadow': ('Bayangan', 'Shadow'),
    'radius_authoritative': ('Otoritatif', 'Authoritative'), 'degraded': ('Terganggu', 'Degraded'),
}.items():
    add(f'enums.enforcement_mode.{v}', a, b)
for v, (a, b) in {
    'healthy': ('Sehat', 'Healthy'), 'disturbed': ('Terganggu', 'Disturbed'),
    'unmonitored': ('Tidak terpantau', 'Unmonitored'), 'stale_data': ('Data usang', 'Stale data'),
    'management_unreachable': ('Manajemen tidak terjangkau', 'Management unreachable'),
}.items():
    add(f'enums.monitor_group.{v}', a, b)
for v, (a, b) in {
    'active': ('Aktif', 'Active'), 'suspended': ('Ditangguhkan', 'Suspended'),
    'disabled': ('Dinonaktifkan', 'Disabled'), 'expired': ('Kedaluwarsa', 'Expired'),
}.items():
    add(f'enums.account_state.{v}', a, b)
for v, (a, b) in {
    'unknown': ('Password belum diketahui', 'Password unknown'), 'ready': ('Siap', 'Ready'),
    'rotation_pending': ('Menunggu rotasi', 'Rotation pending'),
}.items():
    add(f'enums.credential_state.{v}', a, b)
for v, (a, b) in {
    'routine': ('Rutin', 'Routine'), 'manual': ('Manual', 'Manual'), 'pre_change': ('Pra-perubahan', 'Pre-change'),
}.items():
    add(f'enums.backup_category.{v}', a, b)
for v, (a, b) in {
    'scheduled': ('Terjadwal', 'Scheduled'), 'creating': ('Membuat', 'Creating'),
    'transferring': ('Mentransfer', 'Transferring'), 'verifying': ('Memverifikasi', 'Verifying'),
    'committed': ('Tersimpan', 'Committed'), 'expired': ('Kedaluwarsa', 'Expired'),
    'failed': ('Gagal', 'Failed'), 'abandoned': ('Ditinggalkan', 'Abandoned'), 'staging': ('Staging', 'Staging'),
}.items():
    add(f'enums.backup_state.{v}', a, b)
for v, (a, b) in {
    'submitted': ('Menunggu verifikasi', 'Awaiting verification'), 'reviewing': ('Sedang ditinjau', 'Under review'),
    'approved': ('Disetujui', 'Approved'), 'revision_requested': ('Perlu perbaikan', 'Revision requested'),
    'rejected': ('Ditolak', 'Rejected'),
}.items():
    add(f'enums.submission_state.{v}', a, b)
for v, (a, b) in {
    'free': ('Gratis', 'Free'), 'pending': ('Menunggu', 'Pending'), 'active': ('Aktif', 'Active'),
    'grace': ('Masa tenggang', 'Grace'), 'restricted': ('Dibatasi', 'Restricted'), 'ended': ('Berakhir', 'Ended'),
}.items():
    add(f'enums.subscription_state.{v}', a, b)
for v, (a, b) in {
    'discovered': ('Ditemukan', 'Discovered'), 'selected': ('Dipilih', 'Selected'),
    'adopted': ('Diadopsi', 'Adopted'), 'ignored': ('Diabaikan', 'Ignored'),
    'conflict': ('Konflik', 'Conflict'), 'stale': ('Usang', 'Stale'),
}.items():
    add(f'enums.discovery_state.{v}', a, b)
for v, (a, b) in {
    'pppoe': ('PPPoE', 'PPPoE'), 'hotspot': ('Hotspot', 'Hotspot'), 'any': ('Perlu ditinjau', 'Needs review'),
}.items():
    add(f'enums.service.{v}', a, b)
for v, (a, b) in {
    'ok': ('Klien sehat', 'Client healthy'), 'missing_client': ('Klien tidak terpasang', 'Client missing'),
    'degraded': ('Klien tidak lengkap', 'Client incomplete'),
}.items():
    add(f'enums.radius_client.{v}', a, b)
for v, (a, b) in {
    'up': ('Naik', 'Up'), 'down': ('Turun', 'Down'), 'unknown': ('Tidak diketahui', 'Unknown'),
}.items():
    add(f'enums.vpn.{v}', a, b)
    add(f'enums.api.{v}', a, b)
# job_state: microcopy UI_UX.md §12
for v, (a, b) in {
    'queued': ('Menunggu giliran', 'Queued'),
    'claimed': ('Diproses', 'Processing'),
    'preflight': ('Pemeriksaan awal', 'Preflight'),
    'executing': ('Menjalankan', 'Executing'),
    'verifying': ('Memeriksa hasil', 'Verifying'),
    'waiting_dependency': ('Menunggu dependency', 'Waiting on dependency'),
    'retry_wait': ('Akan dicoba lagi', 'Retrying soon'),
    'uncertain': ('Hasil belum pasti', 'Outcome uncertain'),
    'recovery_required': ('Perlu pemulihan', 'Recovery required'),
    'succeeded': ('Selesai — terverifikasi', 'Succeeded — verified'),
    'failed': ('Gagal', 'Failed'),
    'cancelled': ('Dibatalkan', 'Cancelled'),
}.items():
    add(f'enums.job_state.{v}', a, b)

# ============ tulis ============
id_out = {k: v[0] for k, v in MSGS.items()}
en_out = {k: v[1] for k, v in MSGS.items()}

(LOCALES / 'id').mkdir(parents=True, exist_ok=True)
(LOCALES / 'en').mkdir(parents=True, exist_ok=True)
(LOCALES / 'id' / 'web.json').write_text(
    json.dumps(id_out, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
(LOCALES / 'en' / 'web.json').write_text(
    json.dumps(en_out, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(f'Ditulis {len(MSGS)} kunci ke locales/id/web.json dan locales/en/web.json')
