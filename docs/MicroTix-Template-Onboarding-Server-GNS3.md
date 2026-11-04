# MicroTix — Template Onboarding Server/GNS3 v2.1

Tanggal revisi: 29 Oktober 2026, Asia/Jakarta.
Pasangan normatif: `MicroTix-File-1-Kontrak-Revisi-Lengkap.md`, versi2.1.
Status awal: `DRAFT`; belum merupakan pemberian izin mengakses atau mengubah server.

## 1. Fungsi dan penanda perubahan

[REVISI ONB-01 / AUD-03–04] Formulir ini mengikat target, jalur akses, operasi, waktu, resource dan hasil yang diminta. Isi satu nilai konkret pada setiap field yang wajib untuk scope yang dipilih. Tidak ada pilihan tersirat dari teks “VPN/SSH/TBD”. `null` berarti belum diketahui; `[]` berarti tidak ada elemen yang diizinkan; `false` berarti tidak diizinkan. Nilai tersebut tidak boleh dianggap wildcard.

Dokumen dapat selesai diaudit dalam keadaan DRAFT. Satu kali perintah untuk eksekusi server baru dapat berakhir COMPLETED jika input, akses, aset, aplikasi, alat uji dan seluruh prasyarat scope memang tersedia. Jika belum, agent menghasilkan BLOCKED dengan alasan tepat dan melanjutkan pekerjaan independen; agent tidak mengarang fakta atau persetujuan.

[REVISI ONB-02 / AUD-15] Jangan isi password, API key, private key, session token, token enrollment, secret RADIUS, password layanan atau data pelanggan. `secret_bindings` hanya berisi nama logical binding dan rujukan penyedia yang tidak mengungkap nilainya. Kredensial diinjeksi saat runtime melalui kanal terotorisasi. Nama host, CIDR, public key/fingerprint dan versi perangkat adalah metadata akses yang boleh dicatat dalam dokumen privat ini.

## 2. Manifest input tunggal

[TAMBAHAN ONB-03] Blok YAML berikut adalah satu-satunya sumber nilai input. Tabel/uraian setelahnya menetapkan validasi, bukan nilai alternatif. Jangan menduplikasi manifest dengan dua versi berbeda. Unknown key, key duplikat, tipe salah atau nilai placeholder literal seperti TBD/CHANGE_ME/<host> adalah invalid.

```yaml
schema_version: "2.1"
document_contract_version: "2.1"
manifest_id: null
manifest_state: DRAFT
mode: B
requested_outcome: lab_validation

authorization:
  authorization_id: null
  granted: false
  granted_by: null
  grant_proof_ref: null
  granted_at_utc: null
  valid_from_utc: null
  expires_at_utc: null
  permitted_target_ids: []
  permitted_operations: []
  permitted_test_ids: []
  permitted_fault_ids: []
  application_deploy_allowed: false
  application_code_changes_allowed: false
  network_egress_allowed: false
  raw_capture_allowed: false
  local_account_delete_allowed: false
  external_messaging_allowed: false
  production_change_allowed: false
  approved_scope_sha256: null

contacts:
  accountable_owner: null
  technical_contact_ref: null
  recovery_operator_ref: null

targets:
  gns3:
    target_id: null
    host_alias: null
    environment: null
    expected_host_identity: null
    allowed_management_ips: []
    access_kind: null
    jump_target_id: null
    ssh_port: null
    ssh_host_key_sha256: null
    api_base_url: null
    api_family: null
    api_auth_kind: null
    tls_ca_bundle_ref: null
    tls_certificate_sha256_hex: null
    approved_inventory_paths: []
    permitted_existing_project_ids: []
    compute_target_ids: []
  application:
    target_id: null
    host_alias: null
    environment: null
    expected_host_identity: null
    allowed_management_ips: []
    access_kind: null
    jump_target_id: null
    ssh_port: null
    ssh_host_key_sha256: null
    base_url: null
    tls_ca_bundle_ref: null
    expected_commit: null
    expected_artifact_sha256: null
    source_repository_ref: null
    runner_repository_path: null
    deployment_kind: null
    service_allowlist: []
    read_only_inventory_allowed: false

network:
  management_cidrs: []
  aut_cidrs: []
  lab_tunnel_cidr: null
  synthetic_wan_cidrs: []
  customer_test_cidrs: []
  forbidden_cidrs: []
  port_rules: []
  egress_rules: []
  production_bridge_allowed: false
  peer_to_peer_allowed: false
  customer_default_route_via_saas_allowed: false
  ipv6_test_enabled: false
  radius_primary_ip: null
  radius_secondary_ip: null
  radius_secondary_failure_domain: null
  receiver_ip: null
  receiver_port: null
  acs_public_test_url: null
  approved_wan_probe_ips: []

assets:
  images: []
  physical_devices: []
  license_proof_refs: []
  package_mirror_rules: []

runtime_inputs:
  secret_bindings: []
  synthetic_data_only: true
  fixture_seed: 261029
  required_database_major: 17
  required_routeros_major: 7
  required_freeradius_series: "3.2"
  exact_versions_observed_ref: null
  clock_max_skew_seconds: 5

resource_budget:
  max_vcpu: null
  max_ram_mib: null
  max_disk_mib: null
  min_free_disk_after_allocation_mib: null
  max_parallel_projects: null
  max_parallel_nodes: null
  max_auth_requests_per_second: null
  max_accounting_requests_per_second: null
  max_egress_mib: null
  max_cost_idr: null
  max_run_seconds: null
  max_disruption_seconds: null
  abort_host_cpu_percent: null
  abort_host_ram_percent: null
  resource_sample_interval_seconds: 5
  resource_violation_sustain_seconds: 30

execution_plan:
  lab_profiles: []
  test_ids: []
  feature_scope: []
  fault_ids: []
  gate_targets: []
  change_window_start_utc: null
  change_window_end_utc: null
  readiness_timeout_seconds: 120
  allow_dependency_subset_run: true
  retain_owned_lab_on_failure: false

recovery:
  backup_owner_ref: null
  snapshot_provider: null
  approved_snapshot_scope_ids: []
  baseline_snapshot_refs: []
  snapshot_capability_verified_ref: null
  recovery_access_binding: null
  rollback_runbook_ref: null
  kill_switch_method_ref: null
  cleanup_owned_resources_allowed: false
  restore_shared_host_allowed: false
  emergency_operations: []
  emergency_authorization_expires_at_utc: null
  cleanup_deadline_seconds: 600

evidence:
  store_kind: null
  approved_path_or_store_ref: null
  access_policy_ref: null
  encryption_binding: null
  raw_capture_ttl_seconds: 86400
  retain_gate_until_superseded_plus_days: 90
  reviewer_type: self_review
  reviewer_ref: null
  professional_review_refs: []

observed_inventory:
  state: NOT_COLLECTED
  collected_at_utc: null
  target_identity_checks: []
  os_and_kernel: []
  gns3_controller_version: null
  gns3_compute_versions: []
  gns3_api_schema_sha256: null
  kvm_available: null
  nested_virtualization_available: null
  available_resource_snapshot_ref: null
  deployed_commit_or_artifact: null
  effective_dependency_lock_ref: null
  current_routes_and_firewall_ref: null
  image_hash_checks: []
  readiness_report_ref: null
```

## 3. Tipe, enum, dan record daftar

[TAMBAHAN ONB-04] Semua ID berupa string unik; manifest_id, authorization_id dan run_id memakai UUID. Semua timestamp UTC format RFC3339 berakhiran Z; durasi integer detik; resource integer; nominal biaya string decimal IDR dua digit pecahan. CIDR/IP harus valid menurut IP parser, tanpa nama host tersisip. Hash artifact/scope berupa64 karakter hex lowercase; fingerprint SSH memakai format OpenSSH `SHA256:base64`, bukan hash hex sertifikat TLS.

Enum:

| Field | Nilai yang diizinkan |
|---|---|
| manifest_state | DRAFT, AUTHORIZED, REVOKED, EXPIRED |
| mode | A, B, C |
| requested_outcome | documentation_audit, inventory_only, lab_validation, implementation |
| environment | isolated_lab, development, staging, production |
| access_kind | vpn_ssh, ssh_tunnel, jump_ssh, private_https |
| api_family | v2, v3; null hanya sebelum discovery yang terotorisasi |
| api_auth_kind | basic, bearer, mtls, none_private_only |
| deployment_kind | compose_systemd, systemd, predeployed |
| radius_secondary_failure_domain | same_host_process, independent_host |
| store_kind | private_filesystem, private_artifact_store |
| reviewer_type | self_review, independent_human, independent_agent, professional |
| observed_inventory.state | NOT_COLLECTED, COLLECTED, MISMATCH, BLOCKED |

`permitted_operations` adalah subset berikut: `READ_INVENTORY`, `CREATE_PROJECT`, `START_OWNED_NODE`, `STOP_OWNED_NODE`, `LAB_CONFIG_WRITE`, `DEPLOY_SYNTHETIC_AUT`, `CREATE_SYNTHETIC_FIXTURE`, `SNAPSHOT_OWNED`, `FAULT_INJECTION`, `RESTORE_OWNED`, `DELETE_OWNED`, `COLLECT_SANITIZED_EVIDENCE`. Operasi yang tidak tercantum ditolak. Tidak ada wildcard ALL. ModeA menggunakan daftar kosong; tugas dokumentasi lokal tidak memerlukan server grant.

Format setiap record daftar:

- `port_rules`: `{source_target_id, source_cidr, destination_target_id, destination_ip, protocol, destination_port, direction, purpose}`; protocol tcp/udp/icmp, port integer1..65535 atau null untukicmp, direction ingress/egress. Tiap record hanya satu source dan satu tujuan. Loopback diperbolehkan hanya bagi komunikasi lokal yang disebut eksplisit, bukan egress connector tenant.
- `egress_rules/package_mirror_rules`: `{hostname, resolved_ip_allowlist, protocol, port, purpose, max_bytes}`; HTTPS dengan TLS valid. Kebutuhan DNS/NTP juga dicantumkan; blokir metadata, redirect dan jaringan di luar aturan.
- `images`: `{image_id, role, version_exact, architecture, local_path_ref, sha256, size_bytes, license_proof_ref, required_ram_mib, required_vcpu}`. role chr/linux_client/linux_gateway/cpe_emulator. Path wajib berasal dari approved_inventory_paths; regular file tanpa symlink keluar scope.
- `physical_devices`: `{device_id, target_id, vendor, model, firmware_exact, serial_ref, data_model, permitted_capabilities}`; belum tersedia berarti daftar kosong, sehingga uji model fisik BLOCKED.
- `secret_bindings`: `{binding_id, purpose, provider_ref, injection_kind, target_ids, expires_at_utc}`; injection_kind env/fd/agent_socket/secret_mount. Jangan menulis nilai rahasia. Semua target_refs harus ada.
- `baseline_snapshot_refs`: `{target_id, resource_id, snapshot_ref, created_at_utc, restore_verified_ref}`. Snapshot listing bukan bukti restore_verified.
- `target_identity_checks`: `{target_id, identity_method, expected_fingerprint, observed_fingerprint, result}`; result MATCH/MISMATCH. Tidak ada penentuan identitas hanya dari banner hostname.
- `image_hash_checks`: `{image_id, expected_sha256, observed_sha256, result}`.
- `professional_review_refs`: `{domain, reviewer_identity_ref, approved_rule_version, report_ref, approved_at_utc}`; domain accounting/legal. Ini hanya diisi jika review benar-benar tersedia.

Field *_ref menunjuk artefak atau sumber nonrahasia yang dapat diakses agent di dalam scope. String yang terlihat sah tetapi rujukannya tidak tersedia adalah blocker; tidak dianggap memenuhi prasyarat hanya karena tidak null.

## 4. Validasi bertahap sebelum aksi

[REVISI ONB-05] Jalankan validator sesuai tahap, sehingga versi actual yang baru dapat diketahui lewat inventaris tidak menyebabkan deadlock pra-inventaris.

| Tahap | Field dan pemeriksaan wajib | Hasil jika gagal |
|---|---|---|
| V0 dokumen | schema/version cocok2.1; YAML dapat diparse; tidak ada duplicate/unknown key/placeholder/secret literal; referensi dokumen pasangan tersedia | INVALID_INPUT; jangan akses server |
| V1 izin inventaris | outcome bukan documentation_audit; stateAUTHORIZED; granted=true; pemberi/grant proof nyata; waktu valid; target ID/host identity/IP/jalur/port/credential binding jelas; READ_INVENTORY tercakup; scope hash cocok | BLOCKED dengan path field; tidak mencoba login |
| V2 observasi read-only | autentikasi host/pin; target identity MATCH; klasifikasi environment dan versi actual; controller/compute/API kompatibel; inspeksi hanya jalur/service yang diizinkan; tidak dump DB/secret | BLOCKED atau MISMATCH; hentikan target terkait |
| V3 rencana lab | environment nonproduksi; daftar lab/test/operasi subset grant; route/firewall/egress terdefinisi; images+hash+lisensi; app/runner tersedia; resource budget lengkap; window cukup; evidence sink dapat ditulis; backup/snapshot+restore capability tersedia | BLOCKED; jangan provision atau mutasi |
| V4 eksekusi | dependency kasus lulus; capability/build sesuai; snapshot aktual; scope masih valid; expected/actual+cleanup disiapkan; budget/deadline cukup untuk satu langkah aman | BLOCKED untuk case; lanjut case independen |
| V5 penutupan | stop harness; reconcile uncertain; cleanup resource owned; diff listing; evidence hash/redaksi; reviewer_type faktual; laporan terminal | FAILED bila invariant dilanggar; selain itu BLOCKED bila cleanup/review wajib belum selesai |

`approved_scope_sha256` dihitung dari manifest input yang telah dikanonisasi sebagai JSON RFC8785, dengan mengecualikan field approved_scope_sha256 itu sendiri dan seluruh observed_inventory. Setelah AUTHORIZED, perubahan target, operasi, test, fault, window, asset, budget, recovery, secret-binding metadata atau evidence policy memerlukan grant baru/extend yang eksplisit; hasil observasi tidak mengubah grant. Keberadaan hash tidak membuktikan otorisasi tanpa grant_proof_ref yang sah.

Scope durasi minimum menghitung deployment+readiness+setup+test+evidence+cleanup; B3 membutuhkan1800detik danB4 membutuhkan86400detik waktu nyata. Perhitungan unit dengan fake clock tidak boleh menggantikan waktu observasi lab. Window tidak cukup→BLOCKED sebelum langkah mulai, bukan mempercepat simulasi dan mengklaim gate runtime.

## 5. Aturan target, aplikasi, jaringan, dan versi

[REVISI ONB-06] Production tidak eligible untuk Mode B, termasuk inventory melalui Mode B. Pembacaan atau perubahan produksi memerlukan mandat terpisah yang secara eksplisit menyebut target, scope dan operasi; alamat host atau `production_change_allowed=true` pada template bukan mandat. Implementasi/pilot produksi memakai change plan terpisah dan bukti gerbang. Tidak ada router pelanggan menjadi fixture lab.

Host GNS3 dan aplikasi boleh sama hanya jika identitas yang sama dinyatakan dan isolasi/resource memenuhi; jika terpisah, kedua jalur/firewall harus diinventarisasi. Application under test wajib commit/artifact yang dapat dilacak. ModeB tanpa application_deploy_allowed dan DEPLOY_SYNTHETIC_AUT hanya memakai aplikasi predeployed; aplikasi/runner tidak tersedia→BLOCKED, bukan diam-diam menulis kode atau menjalankan compose up. Implementasi memerlukan ModeC dan authorization untuk workspace terkait.

[REVISI ONB-07] GNS3 family diamati pada endpoint versi yang disetujui; jangan menebak v2. Controller/compute versi persis, API schema, image hash, KVM dan lisensi dicatat. CHR adalah RouterOS nyata virtual untuk pengujian protokol, bukan bukti radio/ASIC/kapasitas router fisik. Firmware/model yang belum teruji tetap unsupported pada fitur terkait.

Subnet contoh File1 bukan alokasi aktual. Prefix100.127.0.0/16 harus diperiksa terhadap CGNAT/VPN/host. Peer WireGuard memakai daftar tujuan server /32 yang nyata, tanpa0.0.0.0/0; dua alamat RADIUS harus mempunyai jalur dan secret masing-masing. Sekunder satu host hanya redundancy proses. Customer PPPoE menggunakan klien PPPoE pada L2, bukan DHCP dan bukan peer manajemen WG. Mode IPv6=false membuat uji full dual-stack BLOCKED bila diperlukan untuk klaim isolir penuh; jangan memakai NOT_APPLICABLE untuk menutupi jalur bypass.

Port publik dan privat harus tercantum per rule. ACS publik default HTTPS443 pada hostname khusus;7547 internal kecuali scope eksplisit memilih lain. NBI, Mongo, DB, RADIUS, metrics dan controller tidak dibuka publik. Nama endpoint dari CPE/router tidak otomatis mengizinkan egress.

## 6. Urutan eksekusi tanpa konfirmasi berulang

[REVISI ONB-08] Setelah V0–V3 lulus dan grant memang mencakup aksi, jangan menambah approval checkpoint interaktif yang tidak ada dalam mandat. Catat preview sebagai artefak, lalu jalankan:

1. Buat run_id UUID dan snapshot input/scope/effective config; periksa izin masih berlaku.
2. Read-only inventory dan integrity/version/image checks. Perbedaan expected identity/pin/hash adalah blocker, bukan alasan mengganti expected dengan observed.
3. Siapkan project lab owned, rute sempit, secret injection dan fixtures bila operation grant mengizinkan.
4. Smoke aplikasi dasar: health/commit, DB/RLS/membership, i18n, outbox/job, evidence sink dan waktu. Smoke tidak mensyaratkan router ter-enroll sebelum test bootstrap.
5. Jalankan integration negative tenant T10 dan RADIUS transport baseline T19/T16 menggunakan NAS harness yang legal. Harness non-CHR tidak menghasilkan verified_lab RouterOS.
6. T01 pada CHR existing untuk bootstrap; sesudah itu smoke API pin/tunnel dan pengujian melalui NAS sebenarnya. Jangan membentuk dependency sirkular smoke-router↔bootstrap.
7. Cutover T17 hanya setelah T01/T16/T18/T21 dan backup/rollback prerequisite relevan memenuhi scope; canary dan observasi nyata. Urutan test boleh memakai fixture authoritative yang diprovision khusus untuk membuktikan T18/T21 sebelum test cutover; fixture itu tidak dianggap hasil cutover.
8. Uji fault/security/performance/restore hanya bila fault IDs, resource target, window dan recovery tercantum. Tidak ada perluasan beban hanya karena CPU masih tersedia.
9. Kumpulkan evidence per assertion; evaluasi gerbang fitur yang diminta; cleanup sesuai ownership; tulis hasil terminal.

ID test input boleh parentT01–T24 atau child exact pada registry64+QA-SEC20. Parent diekspansi ke seluruh child applicable pada feature_scope, bukan subset yang mudah lulus. Dependency tidak tercakup grant→BLOCKED, jangan otomatis memperluas izin ke target/operasi baru. ID yang tidak ada→INVALID_INPUT. Penambahan kasus temuan baru diizinkan sebagai desain dokumen; eksekusi target baru tetap mengikuti grant.

## 7. Penghentian, rollback, cleanup, dan evidence

[REVISI ONB-09] Hentikan pengiriman mutasi baru ketika izin dicabut/expired, target identity berubah, resource melewati budget, risiko keluar subnet muncul, secret bocor, atau evidence wajib tidak dapat ditulis. Stop load harness dahulu, fence dispatcher, simpan bukti, lalu rollback owned resource jika sudah tercakup izin pemulihan. Sisihkan cleanup_deadline_seconds sebelum akhir window. Grant dapat memberi emergency_operations yang hanya berisi STOP_OWNED_NODE, RESTORE_OWNED atau DELETE_OWNED dan emergency_authorization_expires_at_utc tersendiri; itu bukan perpanjangan izin test. Setelah izin normal berakhir, hanya operasi darurat tersebut yang boleh dilakukan sebelum expiry darurat. Pencabutan seluruh grant mengalahkan kedua waktu expiry. Tanpa izin pemulihan yang cukup, jangan mulai langkah yang berisiko melampaui window.

Mengembalikan snapshot project/VM owned berbeda dari restore seluruh host bersama. `restore_shared_host_allowed=false` adalah invariant template; jangan mengubahnya untuk cleanup lab. Jangan menghapus resource berdasarkan prefix nama saja; cocokkan object ID dan run ownership. Jika cleanup gagal, laporkan daftar resource tertinggal dan alasan; jangan mengklaim baseline sudah pulih.

Raw PCAP default tidak diizinkan. Jika diotorisasi, gunakan capture scope sempit dan penyimpanan terbatas; TTL≤86400detik. PAP/CHAP/RADIUS debug dapat membawa material rahasia; pseudonimisasi IP/MAC saja tidak cukup. Export hanya artefak semantik yang sudah disanitasi dan hash artefak itu. Secret sintetis tetap rahasia. Screenshot bukti bayar atau password dilarang sebagai evidence umum.

Self-review tidak berarti reviewer independen. Review akuntan/hukum/human yang diwajibkan gate harus mempunyai artefak valid; jika tidak, gate terkait BLOCKED. ModeB tidak mengaktifkan release flag produksi.

## 8. Output wajib agent

[TAMBAHAN ONB-10] Hasil mesin berupa satu summary JSON ditambah laporan manusia dan evidence index. Bentuk berikut adalah template, bukan hasil eksekusi:

```json
{
  "schema_version": "2.1",
  "manifest_id": null,
  "authorization_id": null,
  "run_id": null,
  "terminal_status": "BLOCKED",
  "scope_completed": [],
  "missing_fields": [],
  "blocked_items": [],
  "tests": [],
  "gates": [],
  "findings": [],
  "evidence_index_ref": null,
  "cleanup_status": "NOT_RUN",
  "remaining_owned_resource_ids": [],
  "reviewer_type": "self_review",
  "release_enabled_changes": [],
  "started_at_utc": null,
  "ended_at_utc": null
}
```

Setiap blocked_item mempunyai `{id,reason_code,field_paths,dependency_ids,next_required_input}`. Reason_code: MISSING_INPUT, NOT_AUTHORIZED, AUTH_EXPIRED, TARGET_MISMATCH, HASH_MISMATCH, VERSION_UNSUPPORTED, IMAGE_OR_LICENSE_MISSING, APP_OR_RUNNER_MISSING, RESOURCE_BUDGET_INSUFFICIENT, DEPENDENCY_NOT_PASSED, EVIDENCE_UNAVAILABLE, REVIEW_REQUIRED, RECOVERY_UNPROVEN, CLEANUP_INCOMPLETE.

Untuk template yang masih DRAFT seperti sekarang: agent hanya dapat menyatakan dokumen telah diaudit; belum ada akses, server siap, test PASS, verified_lab atau release_enabled. Pengisian metadata dan pemberian scope nyata dilakukan sebelum perintah eksekusi berikutnya, bukan dianggap sudah diberikan oleh permintaan audit dokumen ini.

## 9. Ikatan konsolidasi makro 2.1-macro.1

[MAC-01–08] Pasangan kontrak tetap document_contract_version 2.1; paket harus mempunyai revision 2.1-macro.1 pada manifest aktif. Blok YAML tetap DRAFT dan tidak memberi akses. Untuk remote Mode B, seluruh V1–V3 tetap wajib. Profil EXECUTION_PROFILE_READY hanya menghilangkan ketergantungan server bagi uji aplikasi lokal/CI pada workspace yang mempunyai mandat Mode C tersendiri; template Mode B ini tidak memberi mandat tersebut. Rujukan PDP/retensi/RADIUS/pilot/review mengikuti master §23 dan gate final. Hasil reviewer/kanal/lokasi/asset tetap faktual, bukan otomatis diisi.


## 8. Resolver target dan profil lokal — EXE-06

File2 tetap sumber grant/fakta remote. Registry pendamping `sumber/contracts/target-registry.schema.json` memuat target tambahan yang dirujuk jump_target_id/compute_target_ids, dengan manifest_id dan SHA-256 File2; tidak membuat grant kedua. Resolver menyatukan root target dan registry, menolak collision/unknown ID/jump cycle/environment mismatch dan target di luar permitted_target_ids. Setiap access transport memerlukan identity/pin/CA/port/allowlist sesuai schema dan prosedur Execution Design §6. `access_kind=none` hanya untuk deskripsi offline; tidak mengizinkan socket. Profil lokal/CI mengikuti execution-profile.schema.json tanpa target remote/produksi dan tanpa mengisi File2 secara palsu. Dokumentasi schema dapat lengkap saat input nyata masih DRAFT.
