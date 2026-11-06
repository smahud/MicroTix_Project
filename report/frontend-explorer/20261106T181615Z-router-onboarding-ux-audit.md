# Frontend Pattern Report — Router Onboarding UX Audit (Phase-1 planning)

Task ID: frontend-explorer (router onboarding) · Date: 2026-11-06 · Repo: main @ 7d600146bd643b48f41b71ce5412c8d5abb89e06 (read-only exploration, clean tree)
Audience: orchestrator implementing Phase-1 — MikroTik router onboarding UX: Add Router → RouterOS version (v6/v7) → protocol picker (WireGuard now; SSTP/L2TP/OpenVPN shown planned/disabled) → backend-generated script preview + Copy → paste into MikroTik terminal → verification progress with HONEST simulated-vs-verified labeling. Backend generates the script; frontend only renders/copies.

Conventions follow `report/frontend-explorer/20261106TK604-fe-pattern.md`. All facts below come from files actually read; paths + line numbers cited at commit 7d60014.

---

## Section 1 — Current Add Router flow (`apps/web/src/features/routers/RouterNewPage.tsx`, 313 lines)

The enrollment wizard **already exists** — Phase-1 extends it, not rebuilds. Header comment (lines 15–18): "U05 — Enrollment router: Identitas → Prasyarat → Skrip → Menunggu → Siap (UI_UX.md §7). Jangan menulis 'Router terhubung' sebelum handshake DAN API terverifikasi." — the honest-labeling mandate is already encoded.

**5-step wizard**, steps array (lines 64–70), step state `useState(0)` (line 26):
1. **Identitas** — fields in `form` state (lines 30–35): `display_name`, `router_code` (uppercased on input, line 155), `location` (optional), `mode` radio (`read_only` default / `managed`) via `Checkbox type="radio"` inside a `<fieldset>/<legend className="mt-label">` (lines 167–189). `TextInput` with `helper`/`error`/`required`.
2. **Prasyarat** — static bullet list incl. `routers.prereq_v7` "RouterOS v7 bila diketahui; versi lebih lama membatasi fitur" (lines 198–216). *This is where a RouterOS v6/v7 picker naturally slots — the copy already references version choice.*
3. **Skrip** — script preview + copy (see below).
4. **Menunggu** — verification stage polling (see below).
5. **Siap** — success icon + `routers.ready_desc` ("Handshake VPN dan API terverifikasi…") + CTAs (lines 291–307).

**API methods used** (all via `const api = useApi()`):
- `api.createEnrollment(tenantId, { display_name, router_code, location: string|null, mode })` → `RouterEnrollmentDraft`; stores `res.id` in `enrollmentId`, invalidates `['routers', tenantId]`, `setStep(1)` (lines 82–91).
- `api.getBootstrapScript(tenantId, enrollmentId!)` — `useQuery` key `['bootstrap-script', tenantId, enrollmentId]`, `enabled: step >= 2 && !!enrollmentId`, `retry: false` (lines 37–42).
- `api.getEnrollment(tenantId, enrollmentId!)` — key `['enrollment-progress', tenantId, enrollmentId]`, `enabled: step === 3`, **dynamic `refetchInterval`: 2000 ms, `false` once `state === 'discovery_ready'`** (lines 44–49); `useEffect` advances to step 4 (52–54).

**Validation pattern** (lines 72–103): local `errors: Record<string, string | undefined>`; client checks first (`validation.required`, `validation.router_code` with `/^[A-Z0-9-]{2,16}$/`); then server `err.envelope?.field_errors` mapped `field → v[0].message` into the same map. No form library — plain controlled inputs.

**Navigation after create**: none — it's an in-page wizard (no route change until user picks a CTA). Final CTAs: `navigate('/app/${tenantId}/imports/router')` (scan accounts) and `ButtonLink` to `/app/${tenantId}/monitoring` (lines 299–304).

**Permission gate**: `if (!can('routers.enroll')) return <AppShell…><PermissionNotice what={t('permission.routers_enroll')} /></AppShell>` (lines 56–62).

**Script step UI** (lines 218–264): `purpose_summary` bullet list → `<pre className="mt-code">{scriptQ.data.script}</pre>` (line 246) → confidentiality + expiry notes → buttons: Back / **Copy** (`icon="copy"`, `copyScript()`) / "Saya telah menjalankan skrip" → step 3. Expiry: `scriptQ.error != null` → warning banner `routers.script_expired` + "Buat ulang skrip" button that **invalidates the bootstrap-script query** (lines 112, 223–237). Gotcha: "regenerate" is a plain refetch of the same GET — the mock never resets `enrollmentIssuedAt`, so an expired mock enrollment stays expired (mock/adapter.ts:617–619). A real regenerate (new token) needs either a backend POST or mock reset if Phase-1 relies on it.

**Copy implementation** (lines 105–110):
```tsx
const copyScript = () => {
  if (scriptQ.data) {
    void navigator.clipboard?.writeText(scriptQ.data.script);
    toast(t('routers.script_copied'), 'success');
  }
};
```
Note: `?.` optional chaining = silent no-op if `navigator.clipboard` is unavailable (insecure context). No shared clipboard utility exists (see Section 6).

**Stepper markup** (lines 124–139): `<ol className="mt-stepper" aria-label={t('routers.wizard_steps')}>` with `<button className="mt-step [mt-step-done]" aria-current="step" disabled={i > step}>`, index shows `<Icon name="check" size={13}/>` when done. CSS: `primitives/primitives.css:604–653`.

**Waiting step** (lines 266–289): renders `progressQ.data.stage_detail` rows — `t(`routers.stage_${st.code}`)` label + state icon: `checkCircle` (ok, `--mt-success-fg`), `alertCircle` (failed, `--mt-danger-fg`), `spinner` w/ `mt-spinner` (pending, secondary). Honest note key `routers.waiting_note` displayed.

**Import/export pattern** (`features/imports/ImportRouterPage.tsx`, 483 lines): 8-step wizard `STEPS` const + dynamic `imports.step_${s}` keys (lines 21–23, 116); `useSearchParams` holds `?router=` (lines 38–39); radio-card selection pattern (label.mt-card + `borderColor: 'var(--mt-primary)'` highlight, lines 356–373) — **the closest precedent for the protocol picker card UI**; quota `ProgressBar`; final commit via `ConfirmAction` → `api.commitMigration` → navigate to `/app/${tenantId}/jobs/${res.job_id}` (lines 465–479).

---

## Section 2 — RouterDetailPage (`apps/web/src/features/routers/RouterDetailPage.tsx`, 369 lines)

- **Enrollment status**: NOT shown here — enrollment lives entirely in RouterNewPage. Detail page shows post-enrollment health: `PageHeader meta` slot with `EnumBadge group="vpn"` + `EnumBadge group="api"` + `FreshnessLabel observedAt` (lines 121–129), condition banners `routers.cond_tunnel_down` / `cond_api_down` (lines 153–162), description includes `RouterOS ${r.routeros_version ?? t('common.unknown')}` (line 119) — `routeros_version` is display-only, never a form input today.
- **Script preview / copy on detail page: NONE.** No bootstrap script recap, no enrollment re-entry. Tabs: summary / discovered / profiles / interfaces / backup / jobs / audit (lines 100–108). `dl.mt-deflist` info card (router_code, identity, mode, serial, uptime), RADIUS panel card, capability list (`routers.cap_${k}` dynamic keys) (lines 167–249).
- **Polling/refetch patterns**: `radiusQ` `refetchInterval: 30_000` (enabled `tab === 'summary'`, lines 43–48); `jobsQ` `refetchInterval: 5_000` (tab `'jobs'`, 49–54). Mutations `releaseRouter`/`replaceRouter` → toast + `navigate(/app/${tenantId}/jobs/${res.job_id})` + `ConfirmAction` (74–98, 335–365). Release confirm uses `requiresReauth` + `confirmTone="danger"` + `scopeLines`.
- **"Simulated" evidence surfacing**: 
  1. Global `DevMockBanner` in AppShell when `useApiMode() === 'mock'` (AppShell.tsx:291, 318; component at 366–372) — `.mt-devbanner` `role="note"` with key `app.dev_mock_banner`: "MODE PENGEMBANGAN: data yang ditampilkan adalah fixture simulasi — bukan integrasi backend."
  2. Mock bootstrap script first line is itself honest: `'# MicroTix bootstrap — DEV FIXTURE, jangan dijalankan pada perangkat nyata'` (mock/adapter.ts:624).
  3. Wizard honesty: `routers.waiting_note` + `routers.ready_desc` only claim verified after `api_verified`/`discovery_ready`.
  4. **No per-item "simulated vs verified" badge exists anywhere** — `EnrollmentProgress.stage_detail` states are only `pending | ok | failed` (client.ts:118–122). If Phase-1 wants an explicit "simulated" chip per stage, it's a new pattern; the honest-labeling convention to follow is the DevMockBanner + accurate i18n copy, not fabricated success.

---

## Section 3 — API layer: router methods, types, and how to add a new one

### 3.1 Router-related types (`apps/web/src/api/contracts.ts`, banner `/* ---------- Router & enrollment (U05/U06) ---------- */` lines 56–116)
- `EnrollmentMode = 'read_only' | 'managed'` (58)
- `EnrollmentState` = draft | enrollment_issued | bootstrap_pending | tunnel_seen | api_verified | discovery_ready | conflict | expired | revoked (60–69)
- `RouterEnrollmentRequest { display_name; router_code; location?: string|null; mode }` (71–76) — **no `routeros_version` / protocol fields yet; Phase-1 adds them here** (backend owns script generation).
- `BootstrapScript { enrollment_id; script; expires_at; purpose_summary: string[] }` (78–84) — JSDoc: script only for authorized roles; expires 15 min (`enroll.token_ttl_s=900`).
- `RouterHealth { vpn; api; observed_at }` (86–90), `EnforcementMode` (92–96), `RouterSummary` incl. `routeros_version: string | null` (98–109), `RouterDetail extends RouterSummary { identity; capability: Record<string,boolean>; uptime_s; serial }` (111–116).
- Related: `JobKind` includes `discover_router`, `router_release`, `router_replace` (266–279); `DiscoveredAccount` etc. (118–169).

### 3.2 ApiClient methods (`apps/web/src/api/client.ts`)
- **Router enrollment** (166–173): `createEnrollment(tenantId, input: RouterEnrollmentRequest, opts?: MutationOptions): Promise<RouterEnrollmentDraft>`; `getEnrollment(tenantId, enrollmentId): Promise<EnrollmentProgress>`; `getBootstrapScript(tenantId, enrollmentId): Promise<BootstrapScript>`.
- Support types in client.ts: `RouterEnrollmentDraft { id; request; state }` (79–83), `EnrollmentProgress { enrollment_id; state; stage_detail: Array<{ code; state: 'pending'|'ok'|'failed' }> }` (118–122), `JobAccepted { job_id; status_url }` (85–88).
- **Routers** (175–184): `listRouters`, `getRouter`, `releaseRouter`, `replaceRouter` (+ `startDiscovery` 187; migration/harvest 190–211; backups 228–236; RADIUS 236–250).
- Live endpoints (live/adapter.ts:136–163): `POST /tenants/{t}/router-enrollments` (withIdem), `GET /tenants/{t}/router-enrollments/{id}`, `GET …/{id}/bootstrap`; `GET /tenants/{t}/routers`, `GET …/routers/{id}`, `POST …/release`, `POST …/replace`. Comment at 136: "Router enrollment (M3 — backend belum aktif)" — live adapter passes backend errors through unchanged (header comment lines 9–11: not_found → UI shows "belum tersedia", never fake data). Routers registry marked R1-available (line 147).
- Mock (mock/adapter.ts:570–684): enrollment state kept in per-instance `Map`s (137–139); `createEnrollment` → `permissionOr403(tenantId, 'routers.enroll')` + field validation `fail('validation_error', …, fe)`; `getEnrollment` simulates deterministic elapsed-time stages (3 s/stage; `discovery_ready` at 13 s, lines 590–612) with stage codes `['vpn_handshake','api_verify','auth_permission','compatibility']`; `getBootstrapScript` fails `expired` after 900 s, returns WireGuard+RADIUS DEV FIXTURE script (614–633); `listRouters/getRouter` from `ROUTERS` fixture (fixtures.ts:40–93 — three routers incl. one RouterOS 6.49.13); `releaseRouter/replaceRouter/startDiscovery` create simulated jobs via `newJob`/`advanceJob` (220–290).

### 3.3 Exact steps to add a new method with live+mock parity (e.g. protocol-aware enrollment)
1. **Types** in `contracts.ts` under the Router & enrollment banner: e.g. `RouterOSVersion = 'v6' | 'v7'`, `EnrollmentProtocol = 'wireguard' | 'sstp' | 'l2tp' | 'openvpn'`; extend `RouterEnrollmentRequest` (e.g. `routeros_version`, `protocol`); optionally a `ProtocolAvailability` read model. Reuse `CursorPage`/envelope primitives; comments cite docs.
2. **Interface** in `client.ts` `ApiClient` with JSDoc citing the endpoint/permission (pattern: 166–173).
3. **Live adapter** (`api/live/adapter.ts`): `http.post<Path>(`/tenants/${tenantId}/router-enrollments`, input, withIdem(o))` — mutations always via `withIdem(o)` (idempotency-key + CSRF); reads via `http.get`.
4. **Mock adapter** (`api/mock/adapter.ts`): TypeScript **forces implementation** — `class MockApiClient implements ApiClient` (line 118); call `this.permissionOr403(tenantId, 'routers.enroll')` first; validate input with `fail('validation_error', msg, field_errors)`; return `delay(value)`; keep state per-instance in a `Map` (billing precedent, lines 125–140).
5. **Fixtures** in `mock/fixtures.ts` if static data needed (deterministic vs `MOCK_NOW`, fixtures.ts:26–33).
6. **Tests**: add behavior contracts to `src/api/api.test.tsx` (instantiate `new MockApiClient()` — constructor auto-logs-in dev owner, adapter.ts:180–190) or a dedicated colocated file like `src/api/billing-adapter.test.tsx`.

**What the tests enforce** (not interface parity — TS does that):
- `api.test.tsx`: rejects shapes `rejects.toMatchObject({ code: 'validation_error' | 'forbidden' | … })` (46–54, 71–81), job polling state machine with real sleeps (90–100, 10 s timeout), filter behavior (102–110), plus a StatusBadge accessibility contract (label + svg icon, 120–128).
- `billing-adapter.test.tsx` (the newest, most complete template): `beforeEach` = `new MockApiClient()` + `login` + `loginTotp` + `switchTenant(T)` (14–19); then per-feature behavior: filtering, two-step state transitions, guard codes (`conflict` for double decision, `validation_error` for missing reason), allocation limits, receipt issuance (21–98).

Provider (`api/index.tsx`): `ApiProvider` builds `QueryClient` with `staleTime: 15_000, retry: false, refetchOnWindowFocus: false` (20–33); `useApi(): ApiClient` + `useApiMode(): 'mock'|'live'` (41–47). Features never import adapters directly. `API_MODE = import.meta.env.VITE_API_MODE ?? 'mock'`; PROD non-live throws (client.ts:322–330).

---

## Section 4 — Release flags (`apps/web/src/permissions/release-flags.ts`)

Mechanism: `RELEASE_FLAGS` const object → `isReleased(flag: ReleaseFlag)` where `ReleaseFlag = keyof typeof RELEASE_FLAGS` (5–37). Gating style: nav entries `release: isReleased('x')` in AppShell `NAV_GROUPS` (AppShell.tsx:160–164 pattern); inline page conditionals e.g. `if (isReleased('billing')) { cols.splice(...) }` (CustomersPage.tsx:137–148). Header comment: unreleased modules are **hidden**, never displayed as active features.

Full current list (lines 5–31): R1 **true** — `landing, auth, overview, customers, routers, imports, backups, monitoring, jobs, settings, radius, admin`; R2 — `billing: true, activation: true, finance: false, collectors: false`; R3 **false** — `devices, vouchers, agents, fieldops`; R4 — `configuration: false`.

**Gating the protocol picker**: since `routers: true` (R1 released), the recommended pattern is either (a) a new flag (e.g. `router_protocols: false`) added to `RELEASE_FLAGS` + a matching assertion in `release-flags.test.ts` (37–54 asserts specific flags — update it in the same commit or `pnpm test` fails), or (b) inline gating of only the new UI, mirroring the billing-column precedent. For SSTP/L2TP/OpenVPN "planned/disabled": the established affordances are `SelectInput` `options: [{ value, label, disabled?: boolean }]` (Input.tsx:100) or `Button disabled + disabledReason` (Button.tsx:16–17, 50–56 — renders a visible reason next to the control, UI_UX.md §2). Precedent for disabled-but-visible choices exists in SelectInput options; nav-level precedent hides unreleased modules entirely — a visible-but-disabled protocol card with an honest "direncanakan" label fits the `disabledReason` philosophy best.

Permissions relevant to onboarding (`permissions.ts`): `routers.read`, `routers.enroll`, `routers.release`, `routers.configure` (13–16; **do not add new business permissions** — header line 3). `routers.enroll`: owner + technician (59–81); `payments_admin`/accountant/viewer lack it. `SENSITIVE_PERMISSIONS` (131–139) does not include `routers.enroll` — no reauth required for enrollment. UI check: `const { can } = useSession(); can('routers.enroll')` (session.tsx:85–88).

---

## Section 5 — i18n (`apps/web/src/i18n/`)

- Catalogs: flat JSON key→string, `locales/id/web.json` + `locales/en/web.json` (1042 keys each, verified identical key sets). **`id` is the source of truth**; `useT`'s `MessageId = Extract<keyof typeof idWeb, string>` → a literal key missing from `id` is a **compile error** (useT.ts:9). Usage: `const t = useT(); t('routers.copy_script')`, ICU placeholders `t('x', { count })`, never concatenation (useT.ts:14–25). Dynamic enum labels: `useEnumLabel()` → `enums.<group>.<value>` with raw-value fallback (useT.ts:41–56).
- **Router key naming conventions** (from catalogs): `routers.f_<field>` (f_display_name, f_router_code, f_mode), `routers.col_<column>`, `routers.tab_<tab>`, `routers.step_<step>` (step_identity/prereq/script/waiting/ready), `routers.stage_<code>` (stage_vpn_handshake/api_verify/auth_permission/compatibility), `routers.cap_<capability>`, `routers.script_*` (script_title/purpose/expires_note/confidential/expired/regenerate/copied/waiting_cta), `routers.mode_<x>[_hint]`, `routers.prereq_*`, `routers.cond_*`; generic: `common.copy/copy`→"Salin", `common.copied`→"Disalin", `common.continue/back/loading`, `validation.<code>` (validation.required, validation.router_code), `enums.vpn.*`/`enums.api.*`, `permission.<slug>`.
- **Dynamic keys** referenced via template literals (`t(\`routers.stage_${st.code}\`)`, RouterNewPage.tsx:273) must be registered in `scripts/check_i18n.py` `ENUM_VALUES` — existing router prefixes: `'routers.stage_'`, `'routers.cap_'`, `'routers.radius_client_'` (check_i18n.py:60–62). A new dynamic prefix (e.g. `routers.protocol_`) must be added there or `pnpm i18n:check` fails with TEMPLATE-UNRESOLVED / ID-MISSING.
- **Parity enforcement**: `pnpm i18n:check` (check_i18n.py) exits 1 on: keys missing in id OR en, ICU placeholder parity mismatch, unresolved templates, **unused keys in id** (ID-EXTRA, lines 112–155). Additionally `release-flags.test.ts:7–34` asserts id/en identical key sets, placeholder parity, non-empty values.
- Provider: `I18nProvider` wraps `IntlProvider`, locale cookie `mt_locale`, fallback visitor-cookie → Accept-Language → `id` (i18n/index.tsx:28–48); missing translations fall back to `id` text (76–85).

---

## Section 6 — Design system inventory for the onboarding UX

**Multi-step wizard**: there is **no Wizard/Dialog-based wizard primitive** — the established pattern is a **full-page stepper** inside `AppShell` + `mt-card`: `<ol className="mt-stepper">` + `mt-step`/`mt-step-done`/`mt-step-index` buttons with `aria-current="step"` (RouterNewPage.tsx:124–139, ImportRouterPage.tsx:149–164; CSS primitives.css:604–653). Extend `RouterNewPage`'s steps array; add the version/protocol step between Identitas and Prasyarat (or fold into Prasyarat).
`Dialog` (primitives/Dialog.tsx:10–98): `open, onClose, title, children?, footer?, width?` — focus trap, Escape, backdrop-click close, focus restore, body scroll-lock, `role="dialog" aria-modal`; `Drawer` also exported (100–148). Use Dialog for confirmations/modals only.

**Code block display**: `pre.mt-code` (base.css:83–93) — dark navy `#0f2a4a` bg, `#e2e8f0` text, `--mt-font-mono`, `max-height: 320px`, `overflow-x: auto`. Already used for the bootstrap script (RouterNewPage.tsx:246). These hex values are hardcoded (outside token pairs measured by check_contrast.py — see Section 8).

**Copy-to-clipboard**: **NO clipboard utility exists anywhere** — only two ad-hoc call sites: RouterNewPage.tsx:107 and CustomerDetailPage.tsx:413 (`void navigator.clipboard?.writeText(...)` + `toast(..., 'success')`). The password reveal box (`mt-reveal-box`, components.css:569–581) is the styled mono-text + copy-button precedent. Phase-1 should either replicate the two-line pattern or extract a tiny shared helper; note jsdom has no `navigator.clipboard` (the `?.` keeps unit tests safe).

**Toast on copy**: `useToast().toast(message, tone: 'info'|'success'|'warning'|'danger')` — max 4 stacked, 5 s auto-dismiss, `aria-live="polite"` container, `role="status"` items (Toast.tsx:31–38, 45–63). Existing keys: `routers.script_copied`, `common.copied`.

**Button** (Button.tsx:7–58): `variant 'primary'|'secondary'|'danger'|'ghost'`, `size 'md'|'sm'|'icon'`, `icon/iconRight` (IconName), `loading` (spinner + aria-busy), `disabled` + **`disabledReason`** (visible reason note — ideal for planned protocols); `ButtonLink` for navigation-vs-action (61–87). One primary per step (PageHeader JSDoc, PageHeader.tsx:6–8).

**Inputs** (Input.tsx): `Field` (permanent label, helper→error precedence, `aria-describedby`, `role="alert"` errors), `TextInput` (label/helper/error/icon), `SelectInput` (`options: Array<{value,label,disabled?}>`, `placeholderOption`) — **native `disabled` option support for SSTP/L2TP/OpenVPN**, `TextArea`, `Checkbox` (`label`/`hint`, used as radio via `type="radio"`). `Segmented` (Misc.tsx:44–70, `role="group"`, `aria-pressed`) suits a v6/v7 toggle; the ImportRouterPage radio-card (label.mt-card + primary border highlight) suits protocol cards.

**StatusBadge** (StatusBadge.tsx:12–29): `tone 'success'|'warning'|'danger'|'neutral'|'info'`, `label`, optional `icon`/`title` — auto icon per tone; color never the only signal. `EnumBadge` (`group`, `value`, `tone`) renders localized `enums.<group>.<value>` (47–58). `FreshnessLabel` (`observedAt`, `source?`, `staleMinutes=15`) for observation honesty (64–89).

**Other relevant primitives**: `ProgressBar` (value/max/tone/label, `role="progressbar"`, Misc.tsx:177–201), `Tabs`, `Skeleton`, `EmptyState`, `Tooltip`, `Breadcrumb`/`CursorPagination`. `ConfirmAction` (Notices.tsx:37–100): `open/onClose/onConfirm/title/intent/scopeLines?/confirmLabel/confirmTone?/loading?/requiresReauth?/children?`. `PermissionNotice` (10–30).

**Icons available** (Icon.tsx:8–66) incl.: `router, terminal, shield, copy, check, checkCircle, alertTriangle, alertCircle, clock, refresh, lock, key, info, spinner, plus, search, x, download, upload, globe, zap, gauge, layers, link, wifi, server`.

Utility classes: `mt-card mt-card-pad`, `mt-stack`/`mt-stack-sm`, `mt-grid`, `mt-row`/`mt-row-between`, `mt-muted`, `mt-small`/`mt-xs`, `mt-mono`, `mt-deflist`, `mt-banner mt-banner-{info,warning,danger,success}`, `mt-visually-hidden`, spacing via `var(--mt-space-*)`.

---

## Section 7 — Test patterns (vitest) + e2e (Playwright)

**Vitest** — config in `vite.config.ts` test block (61–68): jsdom, globals, setup `./src/test/setup.ts`, **excludes `e2e/**`**. Colocated `*.test.ts(x)`. Current suite: `src/api/api.test.tsx`, `src/api/billing-adapter.test.tsx`, `src/lib/*`, `src/permissions/*`. Run `pnpm test`; `pnpm check:all` = tsc + eslint (--max-warnings 0) + vitest + i18n check + contrast check (package.json:17).
- Component-test provider stack (api.test.tsx:13–22): `IntlProvider locale="id" messages={idWeb}` + `QueryClient({ defaultOptions: { queries: { retry: false } } })` + `MemoryRouter`.
- Adapter behavior tests: `new MockApiClient()` directly; assert `rejects.toMatchObject({ code })`, state transitions, deterministic timing with real `setTimeout` sleeps and extended test timeouts (api.test.tsx:90–100).
- For a new wizard step/dialog: mock-method behavior tests in the adapter-test style + (optionally) a component test rendering the page inside the provider stack; clipboard in jsdom is undefined — pattern's optional chaining tolerates it.

**Playwright e2e** — `apps/web/e2e/playwright.config.ts`: `testDir './specs'`, **`workers: 1`, `fullyParallel: false`, `retries: 0`** (17–19), timeout 60 s, baseURL `http://127.0.0.1:5173`, viewport 1280×720, locale `id-ID`; `webServer` runs `bash serve.sh` with env `MICROTIX_API=http://127.0.0.1:8010` and **`VITE_API_MODE=live`** (28–40).
- **The mock adapter does NOT serve e2e.** `e2e/run.sh` (via `make e2e` / `pnpm e2e`) boots the REAL Django backend: `dev_bootstrap.sh` (PostgreSQL 17 + seeds), exports `E2E_OWN_TENANT_ID`/`E2E_FOREIGN_TENANT_ID` from the DB, optionally seeds a dedicated billing tenant (`seed_billing_e2e` → `E2E_BILLING_TENANT_ID`), starts `runserver 127.0.0.1:8010`, waits on `/api/v1/health/live`, then `pnpm exec playwright test --config e2e/playwright.config.ts` (run.sh:28–81). Vite proxies `/api` → backend (vite.config.ts:40–47). Anti-mock guard: build plugin (vite.config.ts:10–23) + runtime throw (client.ts:328–330).
- Helpers (`e2e/helpers/harness.ts`): `SEEDED_OWNER` (env-overridable), `OWN_TENANT_ID`, `FOREIGN_TENANT_ID`, `login(page, email, password)` — fills labeled fields, clicks "Masuk", waits `/app/<uuid>/overview` + heading "Beranda" (43–50); `readVerificationToken(email, marker)` scrapes console-email log.
- Spec conventions (auth.spec.ts, nav.spec.ts, billing.spec.ts): **Indonesian selectors** (`getByRole('button', { name: 'Masuk' })`, `getByLabel('Email')`), honest empty-state assertions, `test.skip(!ENV, ...)` guards, tenant-isolation probes via `page.request.get` expecting 404 envelope `code === 'not_found'` (auth.spec.ts:37–53), real PDF byte-signature checks (billing.spec.ts:33–41), multi-step flows through dialogs with exact-typed buttons (76–124). nav.spec.ts asserts mobile 360 px drawer behavior. Any new onboarding spec must use Indonesian labels and would need a seeded enrollment-capable tenant; the seeded owner tenant starts with no routers (assert honest empty states).

---

## Section 8 — Accessibility / contrast rules the new UI must satisfy

- **`scripts/check_contrast.py`** (`pnpm a11y:contrast`, part of `check:all`): measures WCAG 2.2 AA contrast for token pairs parsed from `src/styles/tokens.css`: **normal text ≥ 4.5:1; large text & meaningful controls ≥ 3:1** (per UI_UX.md §2). Checked pairs (27–41): text on page/card, secondary text, primary link & primary button text, white on admin navy, all five badge fg/bg pairs, dev-mode banner. **Rule for new UI: use the `--mt-*` token pairs** (`--mt-<role>-fg/-bg/-border` naming; tokens.css header says "jangan diubah sepihak" — don't edit tokens unilaterally). Inline icon colors must reference tokens as existing pages do (e.g. `var(--mt-success-fg)`). The `pre.mt-code` block uses hardcoded `#0f2a4a/#e2e8f0` (~12.9:1) — static and outside the measured pair list; reuse as-is.
- Non-color signaling: StatusBadge/EnumBadge always render text + icon (tested: api.test.tsx:120–128); banners pair icon + text (Icon + `mt-banner-warning` etc.).
- Dialog a11y: focus trap, Escape, restore focus, `aria-modal`, `aria-label` from string title, visually-hidden close label (Dialog.tsx:24–97).
- Forms: permanent labels, helper-before-error, `aria-describedby`, `aria-invalid`, error `role="alert"` (Input.tsx:18–49).
- Stepper/wizard: `aria-current="step"`, disabled future steps, `aria-label` on the stepper list; wizard copy honest per UI_UX.md §7.
- Toasts: `aria-live="polite"` + `role="status"` (Toast.tsx:46–48).
- Buttons: `aria-busy` while loading; `disabledReason` surfaced visually next to disabled controls.
- e2e exercises 360 px viewport (nav.spec.ts) — keep wizard responsive (`mt-grid` auto-fit, hideOnMobile-style patterns).

---

## Section 9 — Ordered checklist for Phase-1 (extend, don't rebuild)

1. **Contracts** (`api/contracts.ts`): add `RouterOSVersion` / `EnrollmentProtocol` unions; extend `RouterEnrollmentRequest` with `routeros_version` + `protocol`; keep `BootstrapScript` as the render/copy contract (backend generates script + `purpose_summary`). Money/time conventions N/A here but keep UTC ISO for `expires_at`.
2. **ApiClient** (`api/client.ts`): extend `createEnrollment` input (no new method needed if the request payload simply grows); add a protocol-availability read only if backend exposes one. JSDoc citing endpoint/permission.
3. **Live adapter**: unchanged request path `POST /tenants/{t}/router-enrollments` with new fields via `withIdem(o)`; `GET …/bootstrap` unchanged.
4. **Mock adapter**: validate new fields (`fail('validation_error', …, fe)`); vary the DEV FIXTURE script by protocol/version (keep the honest first-line comment); keep deterministic stage progression; fix/extend regenerate semantics if needed (issuedAt reset).
5. **RouterNewPage**: insert step(s) — RouterOS v6/v7 (`Segmented` or radio-card) + protocol picker (WireGuard enabled; SSTP/L2TP/OpenVPN visible-disabled with reason — `SelectInput disabled` options, radio-card + note, or `Button disabledReason`); update `steps` array + stepper; keep copy button pattern; keep dynamic `refetchInterval` polling.
6. **Release gating**: decide flag vs inline gating (Section 4); update `release-flags.test.ts` in the same commit if adding a flag.
7. **i18n**: add keys to BOTH `locales/id/web.json` + `locales/en/web.json` (e.g. `routers.f_routeros_version`, `routers.protocol_<x>[_hint|_planned]`, `routers.step_version/protocol`); register new dynamic prefixes in `check_i18n.py` `ENUM_VALUES`; run `pnpm i18n:check` (zero missing/extra).
8. **Honest labeling**: keep `routers.waiting_note`-style copy; per-stage states `pending/ok/failed`; global DevMockBanner covers mock-mode; never claim "terhubung/verified" before `api_verified`; disabled protocols say "direncanakan", not "tersedia".
9. **Tests**: adapter behavior tests (mock) in `api.test.tsx` or a new colocated file following `billing-adapter.test.tsx` (login+totp+switchTenant beforeEach, `rejects.toMatchObject({code})`); optional component test with the provider stack.
10. **Checks**: `cd apps/web && pnpm check:all`.
11. **e2e** (optional): new spec under `e2e/specs/` with `login()` + seeded tenant env; Indonesian labels; honest empty/step assertions; runs via `make e2e` (real backend, workers:1).

### Gotchas summary
- **No clipboard utility** — two ad-hoc `navigator.clipboard?.writeText` sites; optional chaining = silent no-op (fine for jsdom, risky in insecure contexts).
- **Regenerate script = refetch** of the same GET; mock expiry never resets (`enrollmentIssuedAt` fixed) — expired mock enrollments stay expired.
- **Backend M3 enrollment endpoints not yet live** (live/adapter.ts:136 comment) — live mode passes through backend errors; UI must show honest "belum tersedia" states, never fabricated scripts.
- **`useT` type-safety**: key missing from `id` catalog = compile error; dynamic template keys need `check_i18n.py` registration; unused keys fail the check.
- **Release-flag test** hard-asserts flag values (release-flags.test.ts:37–54) — update together with any flag change.
- **e2e = real backend + `VITE_API_MODE=live`**, workers:1, no mock anywhere; seeded owner tenant has no routers.
- **EnrollmentProgress has no "simulated" flag** — simulated-vs-verified honesty today = DevMockBanner (mock mode) + stage states + accurate copy; a new per-stage "simulated" chip would be a new (unprecedented) pattern.
- RouterOS version exists today only as display data (`RouterSummary.routeros_version`); RouterNewPage's prereq copy already mentions v7 vs older limits — the v6/v7 picker has a natural home in step 1.
