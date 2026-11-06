# Backend-Explorer Audit — Router Onboarding / VPN Gateway (Phase-1 directive)

- **Role**: backend-explorer sub-agent (read-only audit; no code modified, no servers/migrations run).
- **Objective**: evidence-based audit of the existing WireGuard host/enrollment + RouterOS API-SSL implementation to inform the P0 directive (Add Router → choose protocol → generated connection script → paste into MikroTik terminal → platform shows VERIFIED connectivity; configurable VPN gateway hostname; later multi-protocol via shared listener ports).
- **Baseline**: branch `main`, SHA `7d600146bd643b48f41b71ce5412c8d5abb89e06`, clean tree (verified at start).
- **Timestamp**: 20261106T182013Z.

All paths are relative to `backend/` unless prefixed with `docs/` or `apps/`.

---

## Q1 — Enrollment/router state machine

### State values (exact strings)

**RouterEnrollment.Status** — `backend/domains/network/models.py:91-99`:
`draft`, `awaiting_bootstrap`, `bootstrapped`, `verifying`, `completed`, `expired`, `failed`, `cancelled`.

**WireGuardPeer.State** — `models.py:175-179`: `pending`, `applied`, `drift`, `removed`.

**Router.Mode** — `models.py:20-22`: `read_only`, `managed` (routers are created `read_only` at finalize, `services.py:642`). **Router.Enforcement** — `models.py:24-28`: `local`, `radius_shadow`, `radius_authoritative`, `degraded`.

**DeviceOperation.Status** — `models.py:276-284`: `planned`, `authorized`, `applying`, `uncertain`, `applied`, `verified`, `failed`, `rolled_back`. NOTE: `DeviceOperation` is defined but **never written** by any handler today (only asserted `count()==0` in `tests/integration/test_migration_flow.py:160-161,310`).

**JobState** (job engine wrapping enrollment verification) — `backend/domains/jobs/models.py:65-77` with `VALID_TRANSITIONS` at `:87-108`; unit-tested in `tests/unit/test_state_machine.py:9-37`.

**DiscoverySnapshot.Status** `models.py:203-207`; **DiscoveryObject.ObjState** `models.py:232-238`.

### Transitions and where they are triggered

| Transition | Trigger | Code |
|---|---|---|
| (create) → `draft` | `EnrollmentCreateView.post` (permission `routers.enroll`, `@idempotent`) → `services.create_enrollment` | `views.py:95-110`; `services.py:202-241` (token CSPRNG 256-bit, hash-only + SecretBox-encrypted `token_ref`, `/32` reserved) |
| `draft` → `bootstrapped` | Router script's `/tool/fetch` callback → `BridgeEnrollCompleteView.post` (sessionless, token in body) → `services.complete_enrollment` | `views.py:211-226`; `services.py:554-621` (atomic consume: status, `wg_public_key`, `consumed_at`, `token_ref=""` at `services.py:596-600`; peer `pending` created `services.py:602-612`; `verify_api_ssl` job enqueued `services.py:616-620`) |
| expired token at bridge → `expired` | same bridge call, token past TTL | `services.py:573-577` |
| replay: same identity on consumed token → logical same result (`bootstrap_accepted`/`completed`, `replay:true`); different identity → 409 | bridge call | `services.py:580-588` |
| `bootstrapped` → `verifying` | job worker `run_claimed` → `VerifyApiSslHandler.execute` | `handlers.py:40-47` (status set at `:45-46`) |
| `verifying` → `completed` + Router created + peer → `applied` | `services.finalize_verification` | `services.py:624-665` (Router create `:638-654`; enrollment update `:655-661`; peer update `:662-664`) |
| peer → `removed`, `Router.released_at` set | `RouterReleaseHandler.execute` / `RouterReplaceHandler.execute` (jobs) | `handlers.py:100-113` and `handlers.py:130-152`; triggered by `RouterReleaseView`/`RouterReplaceView` (`views.py:168-208`) |
| `awaiting_bootstrap`, `failed`, `cancelled` | **never set anywhere** — dead states (only referenced in `services.py:248,253-254` mapping and guards `services.py:584,589`) | — |

### "Verified / ready" vocabulary

- There is **no `CONNECTED_VERIFIED` string anywhere** in the repo (grep confirmed).
- Enrollment completion string: `completed` (`models.py:96`).
- API-facing progress states from `services.enrollment_progress` (`services.py:244-274`): `bootstrap_pending`, `tunnel_seen`, `api_verified`, `discovery_ready`, `expired`, `conflict`; stage codes `["vpn_handshake","api_verify","auth_permission","compatibility"]` (`services.py:48`) are **derived from status, not from real probes**.
- Router "active" = row exists with `released_at=None` (`views.py:63,73`); capability evidence at `models.py:47`.

### simulator=True path

`VerifyApiSslHandler.execute` hard-codes `services.finalize_verification(enrollment, simulator=True)` (`handlers.py:47`). **Yes — the simulator path fully marks the enrollment `completed` and creates the Router** (`services.py:655-661`), i.e. the router becomes "ready"/`discovery_ready`. Evidence is labeled distinctly and honestly:
- `Router.capability = {"source": "simulator"|"device", "verified_lab": False, "api_ssl": True, "wireguard": True}` (`services.py:648-653`);
- `RouterEnrollment.device_identity = {"wg_public_key": ..., "simulator": bool}` (`services.py:659`);
- job result `{"evidence": "simulator"}` (`handlers.py:48`);
- health sample `source=active_adapter_name()` → `simulator` unless `MT_ROUTEROS_ADAPTER=api_ssl` (`services.py:723`; `adapters/routeros/factory.py:22-38`).
Integration test asserts exactly this: `tests/integration/test_enrollment_flow.py:122-123` (`capability["source"] == "simulator"`, `not capability["verified_lab"]`).

---

## Q2 — Models, constraints, secrets, lifecycle

**Router** — `models.py:19-57`:
- Fields: `tenant` FK CASCADE (`:31`), `display_name`, `router_code`, `location/model/routeros_version/identity/serial`, `mode`, `enforcement_mode`, `tunnel_ip` **unique globally** (`:42`), `credential_ref` (`:44`), `api_cert_fingerprint` (`:46`), `capability` JSON (`:47`), `created_at`, `released_at` (`:49`), `replaced_by` self-FK (`:50`).
- Constraints: `uq_router_tenant_code` (tenant, router_code) (`:55`); index `(tenant, released_at)` (`:57`).
- Credential storage: SecretBox AES-256-GCM (`domains/common/crypto.py:33-53`, key from env `MT_SECRET_BOX_KEY`, `crypto.py:24-30`), packed as `apiuser=rtrw-mgmt-<code>;password=...` (`services.py:644-646`). Never plaintext.

**RouterEnrollment** — `models.py:84-133`:
- Fields: `tunnel_ip` **unique** (`:109`), `api_port` default 8729 (`:110`), `token_hash` **unique** SHA-256 (`:114`), `token_ref` SecretBox-encrypted plaintext, cleared on consume (`:115`; `services.py:236,599`), `token_nonce` (`:116`), `token_expires_at` (`:117`), `consumed_at` (`:118`), `wg_public_key` (`:120`), `api_cert_fingerprint` (`:121`), `device_identity` JSON (`:122`), `failure_code` (`:123`), `created_by` (`:124`), `completed_at` (`:126`).
- TTLs: token 24 h (`ENROLL_TOKEN_TTL_S`, `services.py:45`); script render claims 15 min (`BOOTSTRAP_TTL_S`, `services.py:46`; response `expires_at` `services.py:340`) — note the endpoint actually re-serves the same token until consumption/24 h (guard only checks `token_expires_at`, `services.py:284-291`).
- Lifecycle/revocation: one-shot consumption; **no explicit revoke/cancel endpoint** (`cancelled` unused); no rotation of the router API credential after issuance.

**WireGuardHost** — `models.py:136-169` (platform singleton, **no tenant FK**, deliberately outside RLS — `migrations/0004_rls_m3.py:19-20`):
- Fields: `interface_name` (default `mtx-wg0`/`wg0`), `listen_port` (default 51820, `:156`), `subnet_cidr` (default `100.127.0.0/16`, `:157`), `public_key` (`:158`), `private_key_ref` SecretBox (dev fallback only; empty after installer adoption, `services.py:68,156`), `key_source` (`installer_env|generated_dev`, `:150-162`), `adopted_at` (`:163`), `desired_revision`/`applied_revision` (`:164-165`).
- Key rotation: `services.adopt_wg_host_key` — refuses rotation while any active peer exists across tenants (`services.py:101-167`, refusal `:142-150`); idempotent; `--check` mode is mutation-free (`:113-123,151-153`). Management commands: `domains/network/management/commands/adopt_wg_host.py`, `render_wg_config.py`, `probe_wg.py`.
- Host pubkey adoption from env `MT_WG_SERVER_PUBKEY` (settings `microtix/settings.py:200-206`, validated X25519 by `microtix/wg.py:12-29`); dev fallback is an honest deterministic SHA-based value, **not** real X25519 (`services.py:170-181`).

**WireGuardPeer** — `models.py:172-197`:
- `allowed_ip` **unique globally** (`:187`), `public_key` (`:188`) — **no uniqueness constraint on public_key** (grep confirms; uniqueness is only `allowed_ip`), nullable OneToOne `router` for the bridge phase (`:185`, migration `0008`), `enrollment` FK SET_NULL (`:186`), `state`, `desired_revision`/`applied_revision`, `last_handshake_at` (`:192`).

RLS: tenant tables get RLS + composite FKs in `migrations/0004_rls_m3.py:14-61`; the bridge SELECT policy `enroll_bridge` (GUC `app.enroll_bridge`) in `migrations/0007_enroll_bridge_policy.py:11-16`, used at `services.py:565-570`.

---

## Q3 — Script generation

**Implemented.** `services.bootstrap_script(enrollment)` — `services.py:277-347`, served by `GET /api/v1/tenants/{tenant_id}/router-enrollments/{enrollment_id}/bootstrap` (`urls.py:14-18`; view `views.py:132-141`, **creator-only** fetch because the script embeds the plaintext token, `views.py:138-140`).

What it embeds and where the value comes from:

| Script value | Source | Reference |
|---|---|---|
| `srvkey` (server WG public key) | `WireGuardHost.public_key` (env adoption or dev fallback) | `services.py:302`, host from `_wg_host()` `services.py:288` |
| `srvaddr` / endpoint-address | **first host of the WG subnet** (`100.127.0.1`) — i.e. the *tunnel-internal* address, **not** a public hostname/IP | `services.py:297,303,317-319` |
| `endpoint-port=51820` | **hard-coded literal** in the script (model field `listen_port` exists but is not interpolated) | `services.py:318` |
| router-side `listen-port=13231` | hard-coded | `services.py:308,312` |
| API-SSL firewall rule `dst-port=8729` | hard-coded | `services.py:326-327` |
| callback URL `https://MATRIX_HOST/api/v1/bridge/enroll-complete` | env var `MT_PUBLIC_HOST`, fallback `"microtix.example"` — via `_public_host_hint()`; **not** request Host header, **not** config registry, **not** a Super-Admin setting | `services.py:331,336,350-353` |
| enrollment token (plaintext) | decrypted from `token_ref` SecretBox | `services.py:289-295,305,336` |

Script properties: idempotent guards, no reset/reboot, only platform-owned `mtx-wg` objects, narrow input rule from server `/32`, token in POST body (`services.py:298-335`). Known defects for Phase-1 hardening: (a) the first interface-add block references `[/certificate/scep-server/get scep-url]` in a `private-key=` expression — leftover artifact that will error on routers without SCEP (`services.py:307-309`); (b) endpoint-address is the internal tunnel IP, so a real router behind NAT could never reach the server; (c) ports hard-coded.

There is **no protocol parameter** — the generator is WireGuard-only; no SSTP/L2TP/OpenVPN path exists.

---

## Q4 — VPN gateway endpoint/hostname & config registry

- **WireGuardHost model** stores `listen_port` and `subnet_cidr` but has **no public hostname/public IP field** (`models.py:154-166`). The only "public host" notion in the backend is env `MT_PUBLIC_HOST` used solely for the bootstrap callback URL (`services.py:350-353`); it is not in `settings.py` (grep confirms only `services.py` reads it).
- **Config registry**: `domains/config/registry.py` — loads `docs/defaults.json` (path `registry.py:100-104`), types/bounds/scope validated (`registry.py:72-87`), env overrides `MT_OVERRIDE_<key>` (`registry.py:52-62`), snapshot support (`registry.py:67-70`). VPN keys today: `vpn.pool_cidr` (100.127.0.0/16, approved_default_only), `vpn.keepalive_s` (25), `vpn.mtu` (1420) — `docs/defaults.json:80-121`. `render_host_config` reads `vpn.keepalive_s` (`services.py:369,372`).
- **Read API**: `GET /api/v1/meta/config` exposes only pagination/session/job subsets (`domains/config/views.py:40-61`; routes `domains/config/urls.py:6-10`). **There is no write API, no DB-backed settings, no audit trail for config changes** — registry is file + env only. Adding a Super-Admin-editable setting has no existing mechanism to extend; the closest precedents are the `platform_admin` user flag (`domains/identity/models.py:43-44`) and the platform-scoped view pattern (`domains/subscriptions/views.py:126-147`), plus the audit `record()` helper (`domains/audit/models.py`, used e.g. in `tests/contracts/test_api_contract.py:82-86`).

---

## Q5 — Router API endpoints (network/urls.py)

All under `/api/v1` (`microtix/urls.py:15`). Tenant views extend `TenantApiView` (`domains/common/views.py:89-119`): membership resolved (`:33-44`, non-member → generic 404), role permission checked (`TenantPermission`, `:57-86`, member-without-permission → 403), handler executed inside `tenant_scope` RLS transaction (`:101-119`).

| Route | View | Method | Permission | Extra |
|---|---|---|---|---|
| `tenants/{tenant_id}/routers` | `RouterListView` | GET | `routers.read` | released excluded (`views.py:58-64`) |
| `tenants/{tenant_id}/routers/{router_id}` | `RouterDetailView` | GET | `routers.read` | `views.py:67-87` |
| `tenants/{tenant_id}/router-enrollments` | `EnrollmentCreateView` | POST | `routers.enroll` | `@idempotent("router_enrollment_create")` (`views.py:93`) |
| `tenants/{tenant_id}/router-enrollments/{enrollment_id}` | `EnrollmentProgressView` | GET | `routers.enroll` | `views.py:124-129` |
| `tenants/{tenant_id}/router-enrollments/{enrollment_id}/bootstrap` | `EnrollmentBootstrapView` | GET | `routers.enroll` | creator-only (`views.py:138-140`) |
| `tenants/{tenant_id}/routers/{router_id}/discoveries` | `DiscoveryStartView` | POST | `routers.enroll` | idempotent per router (`views.py:147`) |
| `tenants/{tenant_id}/routers/{router_id}/release` | `RouterReleaseView` | POST | `routers.release` | idempotent (`views.py:171`) |
| `tenants/{tenant_id}/routers/{router_id}/replace` | `RouterReplaceView` | POST | `routers.enroll` | idempotent (`views.py:192`) |
| `bridge/enroll-complete` | `BridgeEnrollCompleteView` | POST | **none** (`permission_classes: list = []`, `views.py:218`) | sessionless device callback; RLS bridged via `app.enroll_bridge` GUC (`services.py:565-570`, migration `0007`) |

Permission bundles: `routers.read/enroll/release/configure` in `domains/tenancy/permissions.py:15-18`; role mapping `:54-98` (owner/technician get enroll; viewer read-only). Sensitive-permission reauth list does **not** include router permissions (`permissions.py:42-52`). Authentication is Django session + strict CSRF (`domains/identity/authentication.py:19-36`).

---

## Q6 — OpenAPI contract test

`tests/contracts/test_api_contract.py:9-32`: fetches `/api/schema/?format=json` (drf-spectacular, `microtix/urls.py:22`) and asserts `openapi` version prefix plus path existence for a hardcoded list (auth, jobs, subscription, quotations, meta, health). **No snapshot file** — the schema is generated live; assertions are existence-based. To change when adding endpoints/fields: add the new path strings to the `expected` tuple (`test_api_contract.py:20-32`); no regeneration step. Domain-specific contract suites exist alongside (`tests/contracts/test_billing_contract.py`, `test_customers_contract.py`, `test_ops_contract.py`, `test_radius_contract.py`). Frontend mirror contract: `apps/web/src/api/contracts.ts`.

---

## Q7 — What counts as "verification" today

1. **Token consumption** (the only cryptographic proof): `services.complete_enrollment` — hash lookup, atomic consume, replay semantics (`services.py:554-621`).
2. **`verify_api_ssl` job** — `VerifyApiSslHandler.execute` checks enrollment state and calls `finalize_verification(simulator=True)`; **it performs NO actual API-SSL connection and NO WireGuard handshake check** (`handlers.py:31-48`).
3. **`finalize_verification`** writes the evidence (`services.py:624-665`): CSPRNG API password (`:630`); **synthetic** `api_cert_fingerprint = sha256("api-ssl-cert:" + token_hash[:32])[:64]` — derived from the token hash, not from a real certificate (`:631`); Router row with encrypted `credential_ref` (`:644-647`); `capability` evidence incl. `source`/`verified_lab` (`:648-653`); enrollment `COMPLETED` + `device_identity` (`:655-661`); peer → `applied` (`:662-664`).
4. **Job verify step** — `VerifyApiSslHandler.verify` re-reads DB: router exists, `tunnel_ip` matches, `credential_ref` non-empty, peer `applied` (`handlers.py:50-58`) — DB self-consistency only.
5. **Real TLS/cert-pinning capability exists but is unwired**: `ApiSslAdapter._connect` does TLS with SHA-256 pin comparison (`adapters/routeros/apiclient.py:173-196`), login (`:198-219`), bounded queries; but `run_discovery` builds `RouterContext` **without `cert_pin` and without `api_port`** (`services.py:676-683`), so `Router.api_cert_fingerprint` is never used as a pin in production code (only in unit tests `tests/unit/test_apiclient.py:174,193-198`). Adapter mutations honestly refuse with `*_pending_lab` (`apiclient.py:279-306`).
6. **WG handshake evidence** — `services.probe_handshakes` runs `wg show <iface> latest-handshakes` and updates `WireGuardPeer.last_handshake_at` monotonically, with evidence labeling `host_wg|stub` (`services.py:476-551`); exposed only via ops command `probe_wg`, **not via any API and not part of enrollment verification**.
7. Health samples (`RouterHealthSample`, `models.py:60-81`) written by `run_discovery` with `source=active_adapter_name()` (`services.py:714-724`); surfaced in `router_summary` as `health.vpn/api` up/down/unknown (`views.py:27-55`).

Net: today "verified" == token consumed + peer row `applied` + synthetic fingerprint, with honest simulator labeling (`verified_lab=False`). No API-SSL reachability, no handshake, no real cert pin participates in the enrollment verification path.

---

## Q8 — Test harness (conftest.py) & RLS assertions

`backend/tests/conftest.py`:
- `api_client` — `CsrfAPIClient` seeding CSRF cookie like the SPA (`:40-69`).
- `owner` user (`:72-76`); `tenant_a`/`tenant_b` — Tenant + OWNER Membership + free subscription inside `tenant_scope` (`:79-97`); `auth_client` — force_login + `active_tenant_id` + `auth_at` session (`:100-112`).
- **No ready-made router/WG-host fixture**: integration tests bootstrap routers via the real flow — see `test_enrollment_flow.py:170-189` (`_enrolled_router`: `create_enrollment` → parse token from `bootstrap_script` → POST `/api/v1/bridge/enroll-complete` → `_run_jobs_until("verify_api_ssl")` via `engine.claim_next/run_claimed`, `:19-26`). WG host is created lazily by `_wg_host()` on first use; `test_wg_host.py` manipulates it via `monkeypatch.setattr(settings, "MT_WG_SERVER_PUBKEY", ...)` (`:36-38`) and direct `WireGuardPeer.objects.create` under `tenant_scope` (`:40-46`).
- RLS isolation assertions live in `tests/integration/test_rls.py`: write outside scope blocked (`:14-17`), read outside scope empty (`:20-24`), wrong-tenant context empty (`:27-31`), GUC transaction-local (`:40-44`), nested scope restores outer (`:47-58`), composite FK rejects cross-tenant (`:61-70`), runtime role not superuser/BYPASSRLS (`:73-79`).

---

## Q9 — docs/tasks.json relevant TK IDs

`docs/tasks.json` tasks carry fields `id, release, goal, depends_on, requirements, done_when` — **no status field**; status is tracked in `docs/progress.md`. Relevant IDs (goal excerpts quoted):

- **TK-301** (R1): "Registry peer/alamat unik, token hashed sekali pakai (TTL 15 menit), expiry/revoke/rotation, VPN manager typed, nftables default-deny termasuk RADIUS 1812/1813 dan 3799." done_when: "Unique peer/address, hashed nonce, typed VPN outbox reconciliation and least privilege".
- **TK-302** (R1): "Bootstrap bernamespace idempoten (ROUTEROS.md): preview, validasi enrollment, private key di router, kredensial dibangkitkan di router, mode `read_only`/`manage`, sertifikat api-ssl, pemeriksaan overlap; **tidak menyentuh `/radius`, `/ppp aaa`, profil Hotspot**."
- **TK-303** (R1): "Health tunnel/API/auth/permission/TLS/capability terpisah; U05/U06." done_when: "Tunnel/API/TLS/auth/permission/capability health recorded separately U05/U06".
- **TK-304** (R1): "Klien native API-SSL internal dengan certificate pin dan bounded I/O; REST alternatif default off; custom group teruji; target registry dan pencegahan SSRF."
- **TK-305** (R1): NAT/CGNAT/UDP/IPv6/firewall-reload/replay test suite.
- **TK-307** (R1): "Lifecycle klien NAS (`radius.nas`) bersama enrollment/revoke/replace; rotasi secret…"
- **TK-004** (R1): simulator; done_when: "Simulator result never produces verified_lab; fault after send yields uncertain".
- **TK-002** (R1): bootstrap/backend stack.

`docs/progress.md` statuses: "M3 Enrollment | done" (`:359`), "M3 Release/replace | done" (`:364`), TK-002 done (`:417`), TK-004 done (`:419`); WG host adoption checkpoint "WG-1" at `:196-213` (migration 0009, RLS host excluded, installer pubkey adoption); known limitation: "Tanpa perangkat MikroTik fisik … enrollment/discovery/cutover/API-SSL tetap jalur simulator … T01/T10/T17 belum verified_lab" (`:319`). **No TK exists for multi-protocol onboarding / gateway-hostname setting / connection-script UX** — the P0 directive is new scope.

---

## Q10 — ROUTEROS.md normative constraints (quotes with refs)

- **§2.1**: "Server reserve /32 unik, token acak256 bit hashed dengan TTL … Cek subnet/route overlap termasuk shared address space100.127/16; berhenti bila bentrok".
- **§2.2**: "UI menunjukkan tujuan endpoint dan diff semua objek. Validasi token dan HTTPS server dengan hostname/CA/waktu benar sebelum langkah privileged. Token pada body/kanal rahasia, bukan URL/log/analytics. Skrip bersifat sensitif selama token masih berlaku."
- **§2.3**: "Buat/reuse hanya objek yang ownership+fingerprint cocok: interface WireGuard, peer dengan /32 server yang nyata, alamat tunnel dan route /32 server. Private key dibuat router, tidak dikirim ke platform."
- **§2.4**: "Native API-SSL default; sertifikat dipin dari complete enrollment terautentikasi. … Jangan mematikan verifikasi TLS."
- **§2.5**: "Password CSPRNG … **Jangan menaruh secret literal dalam skrip tersimpan.**"
- **§2.6**: "Aturan input tambahan API-SSL dan UDP3799 hanya server /32 pada interface manajemen … Tidak membuka API publik."
- **§2.7**: "Complete consume token+store peer/credential references+audit/outbox atomik … Replay dengan nonce/router key sama mengembalikan logical enrollment tanpa mengulang secret; identitas berbeda ditolak409. Ulang skrip tidak menggandakan peer/user. Revoke token/peer/API/NAS empat state berbeda."
- **§2.8**: "Health dipisah: tunnel_seen, API TLS, auth, permission, compatible, discovery_ready. **Tunnel aktif saja bukan router siap.** Upgrade read_only→manage skrip pendek bertoken baru…"
- **§3**: "Hanya service pppoe atau any yang dapat diadopsi; any direview per objek; **l2tp/sstp/ovpn dan admin router tetap unmanaged**." (today this scopes *customer-service migration*; a multi-protocol *management tunnel* directive will need an explicit doc amendment.)
- **§4**: "Semua menerima konteks router terdaftar, bukan command/URL bebas." / "Timeout setelah kirim→uncertain, readback, lalu retry hanya bila terbukti belum diterapkan."

---

## Gaps vs the Phase-1 directive

1. **No protocol selection**: enrollment create takes only `display_name/router_code/location/mode` (`views.py:95-110`, `services.py:202-241`); script generator is WireGuard-only.
2. **No configurable VPN gateway hostname**: no field on `WireGuardHost`, no registry key, no Super-Admin write API; the only host value is env `MT_PUBLIC_HOST` (callback URL only) with fake default `microtix.example` (`services.py:350-353`). The WG **peer endpoint-address in the script is the internal tunnel IP** (`100.127.0.1`), which cannot work for a real remote router (`services.py:297,317-319`).
3. **"VERIFIED connectivity" is not evidence-based**: progress states are status-derived (`services.py:244-274`); `verify_api_ssl` performs no API-SSL/handshake check (`handlers.py:31-48`); fingerprint is synthetic (`services.py:631`); `cert_pin`/`api_port` never wired into `RouterContext` (`services.py:676-683`); `probe_handshakes` not exposed via API.
4. **Script defects**: SCEP artifact in first add-block (`services.py:307-309`); hard-coded ports 51820/13231/8729 (`services.py:308,312,318,326`).
5. **Dead states / no revoke UX**: `awaiting_bootstrap/failed/cancelled` never set; no enrollment cancel endpoint; no credential rotation path (TK-301/TK-307 expect revoke/rotation).
6. **Shared listener ports per protocol**: only `WireGuardHost.listen_port` (51820) exists; no per-protocol port registry or dispatch.
7. **Config write path absent** (see Q4) — Super-Admin setting needs a new mechanism (DB-backed + `platform_admin` gate + audit).
8. **TTL inconsistency**: token 24 h vs script response claiming 15-min expiry (`services.py:45-46,340`).
9. **Docs**: multi-protocol management tunnel requires amending ROUTEROS.md §2/§3 (current wording keeps l2tp/sstp/ovpn "unmanaged").

## Recommended smallest-change plan (extend, don't rebuild)

1. **Gateway hostname setting**: add a small DB-backed platform setting (e.g. `domains/config` `PlatformSetting` model: key/value/json, RLS-free, unique key) + `platform_admin`-gated GET/PUT endpoints following the `PlatformApiView` pattern (`domains/subscriptions/views.py:126-147`) + `audit.record()` trail. Seed keys: `vpn.gateway_hostname`, per-protocol `vpn.<proto>.listen_port`, `vpn.public_api_base` (replaces `MT_PUBLIC_HOST`).
2. **Fix bootstrap_script to be endpoint-correct**: `endpoint-address=<gateway_hostname>`, `endpoint-port=<host.listen_port>` (interpolate, stop hard-coding); callback URL from the new setting; delete the SCEP artifact block; keep token-in-body and creator-only fetch as-is (ROUTEROS.md §2.2/§2.5).
3. **Protocol parameter (forward-compatible)**: optional `protocol` on enrollment create (default/only `wireguard`, validated against a registry list), stored on `RouterEnrollment` (new field + migration 0010); script generation dispatches per protocol; Phase 1 ships only the WireGuard renderer.
4. **Real verification evidence (WireGuard hardening)**: in `run_discovery`/future probe job, pass `cert_pin=router.api_cert_fingerprint` and `api_port` into `RouterContext` (`services.py:676-683`); make `verify_api_ssl` optionally run `probe_handshakes` (or a `wg_last_handshake` job) and store evidence in `RouterEnrollment.device_identity` / peer `last_handshake_at`; expose handshake+evidence in `RouterDetailView`; keep `verified_lab=False` honesty labels.
5. **Lifecycle cleanup**: set `awaiting_bootstrap` when the script is fetched (or drop the state), add POST `.../router-enrollments/{id}/cancel` → `cancelled`, and an expiry sweeper; reconcile the 15-min script TTL story.
6. **Contract/tests**: append new paths to `tests/contracts/test_api_contract.py:20-32`; add integration tests reusing the `_enrolled_router` harness (`test_enrollment_flow.py:170-189`) + `test_wg_host.py` monkeypatch pattern; add RLS isolation case for the new settings table if tenant-scoped.
7. **Docs**: update `docs/ROUTEROS.md` §2/§3 and `docs/defaults.json` (new keys with bounds) to authorize multi-protocol management tunnels and the gateway-hostname setting; record the directive as a new TK in `docs/tasks.json`.

— end of report —
