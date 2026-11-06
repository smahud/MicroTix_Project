# TK-604 API Contract Reference — Billing (U09) & Activation (U10)

Task ID: 1-a (read-only explorer) · Repo: `MicroTix_Project` @ `62595f4` · Date: 2026-11-06
Scope: everything the orchestrator needs to build `/app/{tenant}/billing` (three tabs) and `/app/{tenant}/activation` against the **real** TK-601/TK-109 backend.

All facts below were read directly from source; citations are `file:line`. Field names are copied verbatim from serializers/views/tests — nothing invented.

---

## 1. Endpoint table

Base prefix: **`/api/v1`** (root URLconf `backend/microtix/urls.py` includes `domains.billing.urls` and `domains.documents.urls` under `api/v1/`).

| # | Method | Path | Purpose | Permission |
|---|--------|------|---------|------------|
| 1 | GET | `/tenants/{t}/billing/packages` | List billing packages (plain array, no pagination) | `customers.read` |
| 2 | POST | `/tenants/{t}/billing/packages` | Create package (Idempotency-Key) | `services.provision` |
| 3 | PUT | `/tenants/{t}/billing/packages/{package_id}` | Update/deactivate package (Idempotency-Key) | `services.provision` |
| 4 | POST | `/tenants/{t}/services/{service_id}/billing-package` | Attach/detach package to service (Idempotency-Key) | `services.provision` |
| 5 | GET | `/tenants/{t}/services/{service_id}/charges` | List add-ons/discounts (plain array) | `customers.read` |
| 6 | POST | `/tenants/{t}/services/{service_id}/charges` | Add recurring charge (Idempotency-Key) | `services.provision` |
| 7 | PUT | `/tenants/{t}/charges/{charge_id}` | Update/deactivate charge (Idempotency-Key) | `services.provision` |
| 8 | GET | `/tenants/{t}/invoices` | Invoice list + filters (cursor page) | `customers.read` |
| 9 | GET | `/tenants/{t}/invoices/aging` | Aging report vs due date | `customers.read` |
| 10 | GET | `/tenants/{t}/invoices/{invoice_id}` | Invoice detail + lines | `customers.read` |
| 11 | GET | `/tenants/{t}/payments` | Payment list + filters (cursor page) | `customers.read` |
| 12 | POST | `/tenants/{t}/payments` | Record payment (state=submitted; Idempotency-Key) | `payments.verify` |
| 13 | GET | `/tenants/{t}/payments/{payment_id}` | Payment detail + allocations | `customers.read` |
| 14 | POST | `/tenants/{t}/payments/{payment_id}/verify` | Verify funds → allocations + receipt (Idempotency-Key) | `payments.verify` |
| 15 | POST | `/tenants/{t}/payments/{payment_id}/reject` | Reject with reason (Idempotency-Key) | `payments.verify` |
| 16 | GET | `/tenants/{t}/documents` | List issued documents (filters kind/ref_type/ref_id, cursor page) | `customers.read` |
| 17 | GET | `/tenants/{t}/documents/{document_id}` | Download PDF artifact (reprint) | `customers.read` |
| 18 | PATCH | `/tenants/{t}/access-accounts/{account_id}` | Access-account state `suspended↔active` (closest thing to activation; Idempotency-Key) | `services.activate` |

Sources: `backend/domains/billing/urls.py:6-59`, `backend/domains/documents/urls.py:10-17`, `backend/domains/customers/urls.py:15-20`, `backend/domains/billing/views.py:1-19` (endpoint docstring), permission per view class (cited per endpoint below).

**Role → permission matrix** (`backend/domains/tenancy/permissions.py:54-98`):

| Role | customers.read | services.provision | payments.verify | services.activate |
|------|:-:|:-:|:-:|:-:|
| owner | ✅ | ✅ | ✅ | ✅ |
| technician | ✅ | ✅ | ❌ | ❌ |
| payments_admin | ✅ | ❌ | ✅ | ✅ |
| accountant | ✅ | ❌ | ✅ | ❌ |
| viewer | ✅ | ❌ | ❌ | ❌ |

None of these permissions are in `SENSITIVE_PERMISSIONS` (`permissions.py:42-52`) → **no TOTP reauth required** for any billing/payment endpoint. (Only `services.reveal_credentials`, `radius.cutover`, etc. are sensitive.)

---

## 2. Per-endpoint detail

### Conventions (all endpoints)

- **Auth**: session cookie (HttpOnly). Anonymous → `401` `{code:"unauthorized"}`; authenticated but not a member of `{tenant_id}` → `404` generic (`{code:"not_found"}`); member without permission → `403` `{code:"forbidden"}` (`backend/domains/common/views.py:33-44, 71-86`).
- **CSRF**: mutations require `x-csrf-token` header from `mtx_csrf` cookie (frontend `apps/web/src/api/http.ts:62-63`; test client `backend/tests/conftest.py:40-61`).
- **Idempotency-Key header is MANDATORY** on all POST/PUT/PATCH marked "(Idempotency-Key)" above — missing → `422` `field_errors.idempotency_key[0].code == "required"`; >128 chars → `422 max_length`; same key+same body → logical replay of stored response; same key+different body → `409` `code:"idempotency_conflict"` (`backend/domains/common/idempotency.py:37-87`).
- **Error envelope** (`backend/domains/common/envelope.py:76-89`):
  ```json
  {"code": "<machine_code>", "message": "<localized>", "request_id": "...", "locale": "id",
   "field_errors": {"<field>": [{"code": "...", "message": "..."}]},   // optional
   "retryable": false}                                                  // optional
  ```
- **Page envelope** (`backend/domains/common/pagination.py:65-66`): `{"items": [...], "next_cursor": "<opaque>" | null}`. `limit` default **50**, max **200**; `limit<=0` or `>200` → `422` field `limit` (`pagination.py:15-16, 42-62`).
- **Money** is always a **string with 2 decimals** (`"300000.00"`); dates are `YYYY-MM-DD`; datetimes are `isoformat()` with offset. Locale of messages: `request.mt_locale` (default `id`).
- All handler logic runs inside `tenant_scope` (RLS) via `TenantApiView.dispatch` (`common/views.py:101-119`).

### 2.1 GET `/tenants/{t}/invoices` — invoice list (views.py:280-311)

Query params:
- `state` — one of `draft|open|partial|paid|void` (invalid → `422` field `state`, code `invalid`)
- `kind` — `prepaid|postpaid` (invalid → `422` field `kind`)
- `service_id` — UUID (invalid → `422` field `service_id`)
- `period_from` — `period_start >= period_from`
- `period_to` — `period_end <= period_to`
- `limit` — 1..200 (default 50)
- ⚠️ `cursor` is **accepted but ignored** (see Gap G-1)

Sort: `-issued_at, -id`. Response: `{"items": [invoice_info…], "next_cursor"}`.

`invoice_info` (views.py:78-118) — **without** `lines` in list mode:

```json
{
  "id": "uuid-str",
  "doc_number": "INV-<namespace>-202611-0001",
  "service_id": "uuid-str",
  "service_code": "SVC-001",
  "customer_name": "Budi Pelanggan",
  "kind": "prepaid" | "postpaid",
  "state": "open" | "partial" | "paid" | "draft" | "void",
  "period_index": 0,
  "period_start": "2026-12-01",
  "period_end": "2027-01-01",          // exclusive end ([start, end))
  "due_date": "2026-12-01",
  "issued_at": "2026-11-24T03:00:00+00:00",
  "total_amount": "300000.00",
  "paid_amount": "0.00",
  "outstanding": "300000.00",          // computed total - paid (models.py:195-197)
  "first_period_policy": "full",
  "locale": "id",
  "timezone": "Asia/Jakarta",
  "document_id": "uuid-str | null"     // linked invoice PDF (IssuedDocument)
}
```

### 2.2 GET `/tenants/{t}/invoices/{invoice_id}` — detail (views.py:314-327)

Same fields **plus** `lines` (ordered by `ordinal`):

```json
"lines": [
  {"line_kind": "subscription", "name": "Paket Reguler 300rb · 1 Desember 2026 – 31 Desember 2026", "amount": "300000.00", "ordinal": 0},
  {"line_kind": "add_on",          "name": "IP Publik Statis", "amount": "50000.00",  "ordinal": 1},
  {"line_kind": "discount_nominal","name": "Promo Perdana",    "amount": "-20000.00", "ordinal": 2},
  {"line_kind": "discount_pct",    "name": "Diskon 10%",       "amount": "-30000.00", "ordinal": 3}
]
```

Unknown/foreign invoice → `404`. Bad UUID → `422` field `invoice_id` (`views.py:44-48`).

### 2.3 GET `/tenants/{t}/invoices/aging` — aging report (views.py:330-344; services.py:719-764)

Query: `as_of` (optional `YYYY-MM-DD`, default = today; bad format → `422` field `as_of`).
Only invoices in state `open|partial` are included. Response (NOT paginated):

```json
{
  "as_of": "2026-11-06",
  "totals": {
    "not_due":  {"count": 1, "outstanding": "300000.00"},
    "current":  {"count": 1, "outstanding": "300000.00"},   // 0-30 days over due
    "d31_60":   {"count": 1, "outstanding": "300000.00"},
    "d61_90":   {"count": 1, "outstanding": "300000.00"},
    "d90_plus": {"count": 1, "outstanding": "300000.00"}
  },
  "items": [
    {"invoice_id": "uuid", "doc_number": "INV-ns-202611-0001", "service_code": "SVC-AG1",
     "customer_name": "Customer 1", "due_date": "2026-11-01", "days_overdue": 5,
     "overdue": true, "bucket": "current", "outstanding": "300000.00"}
  ]
}
```

Route `invoices/aging` is registered **before** `invoices/{invoice_id}` (`billing/urls.py:31-41`) so "aging" is never parsed as an id.

### 2.4 GET `/tenants/{t}/payments` — payment list (views.py:360-381)

Query: `state` (`submitted|verified|rejected`, invalid → `422`), `method` (`bank_transfer|ewallet|cash|collector_cash`, invalid → `422`), `limit`. ⚠️ No `cursor` support (Gap G-1), no date/service/customer filters (Gap G-7). Sort `-submitted_at, -id`.

`payment_info` (views.py:121-146) — **no customer/service fields, no receipt document_id**:

```json
{
  "id": "uuid-str",
  "method": "cash",
  "state": "submitted",
  "amount": "50000.00",
  "allocated_amount": "0.00",
  "credit": "50000.00",                 // amount - allocated_amount (models.py:292-295)
  "external_ref": "MUT-2026-001 | null",
  "has_proof": false,                    // bool(payment.proof_path)
  "collector_display": "",
  "submitted_at": "2026-11-06T04:00:00+00:00",
  "verified_at": "2026-11-06T05:00:00+00:00 | null",
  "rejected_reason": ""
}
```

### 2.5 POST `/tenants/{t}/payments` — record payment (services.py:471-534)

Body (JSON):

| Field | Type | Rules |
|---|---|---|
| `method` | string | required, one of `bank_transfer\|ewallet\|cash\|collector_cash` (else `422` field `method`) |
| `amount` | string/number | required, > 0, max 2 decimals (else `422` field `amount`, codes `positive`/`max_decimal_places`/`invalid`) |
| `file_b64` | string | **required for `bank_transfer`/`ewallet`** (`422` code `required`); optional for cash; base64-decoded bytes sniffed by magic — PNG/JPEG/WebP/PDF only (else `422` code `mime`); ≤ 5 MiB = 5242880 bytes (else `422` code `too_large`) (`services.py:447-468, 481-501`; `backend/domains/subscriptions/upload.py:18-19`) |
| `mime` | string | optional *claimed* MIME; if provided and not in allowed set → `422` field `mime` (proof is stored first, error raised honestly) |
| `external_ref` | string | optional bank-mutation ref; trimmed to 128; **unique per tenant** → duplicate → `409` `code:"conflict"` |
| `collector_display` | string | only allowed when `method == "collector_cash"` (else `422` field `collector_display`); max 120 |

Success → **201** + `payment_info` with `state == "submitted"` (proof upload ≠ posted payment, BIL-03).
Test assertions: `body["state"] == "submitted"`, `body["credit"] == "50000.00"` (`tests/integration/test_billing_payments.py:106-115`).

### 2.6 POST `/tenants/{t}/payments/{payment_id}/verify` — verify funds (services.py:571-678)

Body:

```json
{"allocations": [{"invoice_id": "<uuid>", "amount": "300000"}, ...]}
```

- `allocations` must be a list (else `422`); each entry a dict with `invoice_id` + positive 2-dp `amount`; **duplicate `invoice_id` entries are merged (summed)** (`services.py:537-555`).
- Payment must exist in tenant → `404`; must be `submitted` → else `409` `code:"billing.payment_decided"`.
- Σ allocations > payment.amount → `409` `billing.allocation_exceeds_payment`.
- Any invoice not found in tenant → `404` (RLS-generic, cross-tenant invoice → 404 not 422 — `test_billing_payments.py:497-523`).
- Invoice state not in `(open, partial)` → `409` `billing.invoice_not_payable`.
- Allocation > invoice outstanding → `409` `billing.allocation_exceeds_outstanding`.
- Empty list `[]` is legal → verified with full credit; receipt still issued (`test_billing_payments.py:353-372`).

Side effects: per invoice `paid_amount += amount`, state → `paid` when `paid_amount == total_amount` else `partial`; `PaymentAllocation` rows created; payment → `state="verified"`, `verified_at` set; **receipt RCP document issued** (BIL-08). Payment never touches service lifecycle.

Success → **200** + `payment_info` **with** `allocations` (views.py:402-418):

```json
"allocations": [
  {"invoice_id": "uuid", "invoice_number": "INV-ns-202611-0001", "amount": "300000.00",
   "allocated_at": "2026-11-06T05:00:00+00:00"}
]
```

### 2.7 POST `/tenants/{t}/payments/{payment_id}/reject` (services.py:681-709)

Body: `{"reason": "..."}` — required non-empty (else `422` field `reason` code `required`); truncated to 2000 chars. Payment must be `submitted` → else `409` `billing.payment_decided`.
Success → **200** + `payment_info` (no `allocations` key) with `state == "rejected"`.

### 2.8 GET `/tenants/{t}/payments/{payment_id}` (views.py:390-399)

→ `payment_info` + `allocations` (allocations exist only after verify; submitted payments return `allocations: []`).

### 2.9 Packages & charges (U09 config side)

**GET `/billing/packages`** → plain **array** of `package_info` (views.py:51-62, 171-173), sorted `created_at, id`:

```json
{"id": "uuid", "name": "Paket Reguler 300rb", "monthly_price": "300000.00",
 "billing_cycle": "fixed_monthly", "timing": "prepaid", "due_day": null,
 "first_period_policy": "full", "active": true, "created_at": "iso-datetime"}
```

**POST `/billing/packages`** body: `name` (1-120 chars, unique per tenant → `409` conflict on duplicate), `monthly_price` (≥0, 2dp), `billing_cycle` (`fixed_monthly` default | `anniversary`), `timing` (`prepaid` default | `postpaid`), `due_day` (int 1-31 or null; **only valid with fixed_monthly** → `422`), `first_period_policy` (`full` default | `prorata_daily` | `free_until_next_period`; `anniversary` + non-`full` → `409` `billing.invalid_policy`). → **201** + `package_info` (services.py:80-141).

**PUT `/billing/packages/{id}`** — merge-patch of the same fields + `active` (bool). → **200**.

**POST `/services/{s}/billing-package`** body `{"package_id": "<uuid>"}` (or empty/null/`""` to detach) → **200** `{"service_id": "...", "billing_package_id": "uuid | null"}` (views.py:192-214).

**GET `/services/{s}/charges`** → plain array of `charge_info` (views.py:65-75):

```json
{"id": "uuid", "service_id": "uuid", "kind": "add_on", "name": "IP Publik Statis",
 "amount": "50000.00", "valid_from": null, "valid_until": null, "active": true}
```

**POST `/services/{s}/charges`** body: `kind` (`add_on|discount_nominal|discount_pct`), `amount` (≥0, 2dp; `discount_pct` ≤ 100), `name` (≤120, default "charge"), optional `valid_from`/`valid_until`. → **201**.

**PUT `/charges/{id}`** body (all optional): `active`, `amount`, `valid_until`. → **200**.

### 2.10 PATCH `/tenants/{t}/access-accounts/{account_id}` (customers/views.py:355-368)

Body: `{"state": "active" | "suspended"}`. Only `suspended↔active` transitions allowed (`customers/services.py:289-294`); `disabled`/`expired` are terminal via this API → `409`. Setting the same state is idempotent (no-op). Success → **204 No Content** (empty body). Bad state value → `422` field `state` code `choice`.

This is currently the **only** activation-ish mutation (see Section 5.7).

---

## 3. Enums / state machines

### Invoice state — `InternetInvoice.State` (billing/models.py:138-143)

`draft` → `open` (issue; `draft` currently unreachable via API) → `partial` (some allocation) → `paid` (paid_amount == total_amount); `void` (enum + `void_reason`/`voided_at` fields exist but **no API voids an invoice**).
Note: invoice with `total_amount == 0` (free_until_next_period) is issued directly as **`paid`** (services.py:373-375).

### Invoice kind — `InternetInvoice.Kind` (models.py:134-136)

`prepaid` | `postpaid` — mirrors the package `timing` that issued it.

### Payment state — `InternetPayment.State` (models.py:246-249)

`submitted` → (`verified` | `rejected`); **terminal** — verify/reject on a decided payment → `409 billing.payment_decided` (services.py:594-596, 689-690).

### Payment method — `InternetPayment.Method` (models.py:240-244)

`bank_transfer` | `ewallet` | `cash` | `collector_cash`.

### BillingPackage enums (models.py:46-57)

- `billing_cycle`: `fixed_monthly` | `anniversary`
- `timing`: `prepaid` | `postpaid`
- `first_period_policy`: `full` | `prorata_daily` | `free_until_next_period`

### ServiceCharge.Kind (models.py:97-100)

`add_on` | `discount_nominal` | `discount_pct`. Invoice line kinds: `subscription`, `add_on`, `discount_nominal`, `discount_pct` (services.py:263-285). Discount lines carry **negative** amounts.

### Aging buckets (services.py:716, 735-745)

`not_due` (due_date in future), `current` (0-30 days over), `d31_60`, `d61_90`, `d90_plus` (>90).

### Service lifecycle / payment dims (customers/models.py:54-70) — for U10 context

- `lifecycle`: `draft|pending|provisioning|provisioned|conflict|failed|terminated|archived`
- `payment_status` (independent dimension): `unbilled|partial|paid|not_billed`
- AccessAccount `state`: `active|suspended|disabled|expired`; only suspended↔active via API.

### `/meta/enums` coverage (backend/domains/i18n/enums.py:8-52)

Exposed groups: `job_state`, `enforcement_mode`, `connection`, `isolation`, `payment` (= Service.payment_status labels), `lifecycle`. **No** groups for invoice state, payment method/state, aging buckets, package cycle/timing/policy, charge kinds → UI must hardcode labels (Gap G-5). Note the `payment` enum labels ("Belum dibayar"/"Sebagian"/"Lunas"/"Tidak ditagih") refer to the *Service dimension*, not InternetPayment states.

---

## 4. Documents / PDF endpoints (TK-109)

### GET `/tenants/{t}/documents` (documents/views.py:49-76)

Query: `kind` (`internet_invoice|receipt|saas_invoice|report`), `ref_type` (exact), `ref_id` (exact), `limit`, `cursor` (**fully supported here**, unlike billing lists). Sort `-issued_at, -id`.

Response `document_info` (documents/services.py:156-170) — **no `storage_path`** (private):

```json
{"id": "uuid", "kind": "internet_invoice", "doc_number": "INV-ns-202611-0001",
 "ref_type": "billing_invoice", "ref_id": "<invoice uuid>", "locale": "id",
 "timezone": "Asia/Jakarta", "template_version": "1", "sha256": "<hex64>",
 "size_bytes": 12345, "issued_at": "iso-datetime"}
```

Test-asserted key set: exactly `{id, kind, doc_number, ref_type, ref_id, locale, timezone, template_version, sha256, size_bytes, issued_at}` (`tests/integration/test_documents_api.py:221-225`). Cursor pagination works: `?limit=2` → `next_cursor` → `?limit=2&cursor=...` (`test_documents_api.py:236-243`). Bad `limit`/`cursor` → `422`.

### GET `/tenants/{t}/documents/{document_id}` (documents/views.py:79-101)

Returns raw **`application/pdf`** bytes (NOT JSON) with `Content-Disposition: inline; filename="<doc_number sanitized>.pdf"`. Reprint is byte-identical (sha256 verified; mismatch/missing file → `500` `code:"document_integrity"`). Unknown id, malformed id, or foreign-tenant document → `404` generic (`test_documents_api.py:255-270`).

### Document linkage rules

| Source | Kind | `ref_type` | `ref_id` |
|---|---|---|---|
| Internet invoice issue | `internet_invoice` | `billing_invoice` | invoice UUID |
| Payment verification | `receipt` | `billing_payment` | payment UUID |

- Invoice → PDF: use `document_id` straight from `invoice_info` (billing/views.py:79-86, 106).
- Payment → receipt: **not** in `payment_info`; look up via `GET /tenants/{t}/documents?kind=receipt&ref_type=billing_payment&ref_id={payment_id}` → `items[0].id` → artifact URL (Gap G-4).
- Doc numbers: `INV-{tenant.namespace}-{YYYYMM}-{seq 4-digit}` / `RCP-{tenant.namespace}-{YYYYMM}-{seq 4-digit}`, serialized per tenant via row lock (`billing/services.py:196-219`).

### PDF content (rendering.py:143-219)

Invoice v1: header tenant_name, doc number, issued/due dates (long-form localized, e.g. "11 Oktober 2026"), bill-to customer_name, service_code, line table (description + IDR), total. Receipt v1: doc number, received-from customer_name, received_at, method (localized), applies_to table (invoice_number + amount), total amount, credit line if non-zero. Money format `Rp1.500.000` (id) / `IDR 1,500,000` (en) — cents suffix only when non-zero.

---

## 5. UI-relevant business rules

1. **Two-phase payment (BIL-03)** — recording a payment (with or without proof) creates state `submitted`, which is NOT a posted payment. Money only reaches invoices at `verify`, which creates `PaymentAllocation` rows, bumps invoice `paid_amount`, and flips invoice `open→partial|paid`. Decision is one-shot: verify/reject on a decided payment → `409 billing.payment_decided`.
2. **Allocation rules** — one payment may allocate to many invoices; duplicate invoice ids in the request are summed; Σ allocations ≤ payment.amount; each allocation ≤ invoice outstanding; only `open`/`partial` invoices are payable (`services.py:537-568`). Partial payment does NOT settle an invoice (stays `partial`).
3. **Credit / overpayment** — unallocated remainder is exposed as `credit` on the payment (`amount - allocated_amount`). Verifying with `allocations: []` is legal → full-credit receipt. Credit is *not* auto-applied later and *not* journalled (M7 TK-701). UI copy per UI_UX §8: overpayment = "Saldo kredit belum dialokasikan" (bukan laba).
4. **Proof upload** — bank_transfer/ewallet MUST include `file_b64` (base64 in JSON, no multipart); sniffed types PNG/JPEG/WebP/PDF, max 5 MiB. Cash may be proof-less. `collector_display` only for `collector_cash`. `external_ref` dedups identical bank events per tenant (409 on repeat) — distinct real transfers stay distinct payments.
5. **Invoice snapshot invariants** — package price/policy are frozen at issue time; later package edits never change issued invoices/lines. One invoice per (tenant, service, kind, period) — UNIQUE constraint. Scheduler is idempotent and catch-up (all due periods issued when it runs).
6. **Invoice math (calendar.py)** — prepaid: issue ≈ start−7d (LEAD_PREPAID_DAYS=7), due = period_start (never before issue); postpaid: issue = period_end, due = issue+7d (POSTPAID_DUE_DAYS=7), `due_day` clamps first on/after due (fixed_monthly only). First period: `full` | `prorata_daily` (price×days/month-days, ceil Rp100) | `free_until_next_period` (0 → invoice state `paid`). Period bounds are `[start, end)` exclusive; fixed_monthly period 0 is partial (activation day → start of next month).
7. **Activation is ALWAYS separate & manual (U10)** — "Pembayaran TIDAK PERNAH mengubah lifecycle service" (`billing/models.py:20-22`, `services.py:14-15`; test `test_payment_does_not_auto_activate`, `test_billing_payments.py:311-329`). What exists today:
   - `PATCH /access-accounts/{id} {"state":"active"}` (perm `services.activate`, 204) — unsuspend an account. 
   - `JobKind.ACTIVATE_SERVICE` exists only as an enum value (`jobs/models.py:24,49`) — **no endpoint enqueues it**.
   - **No** `/services/{id}/activate`, **no** bulk activation, **no** eligibility query: `GET /services?quick_tab=paid_awaiting_activation` deliberately returns an empty set ("beta: belum ada aktivasi tertunda", customers/views.py:260-261).
   - UI can approximate eligibility client-side: invoices with `state == "paid"` for a service (via `GET /invoices?service_id=...&state=paid`) whose service is `provisioned`/account `suspended`.
8. **Refund/correction** — reject requires a reason; "dokumen koreksi disusul" (billing/views.py:428) — no correction document endpoint exists yet.
9. **Aging** — buckets vs `due_date`, `not_due` separated from overdue; only open/partial invoices counted; paid excluded.
10. **Tenant scoping / errors** — every path is `/tenants/{tenant_id}/...`; wrong-tenant URL → 404 generic (never 403); cross-tenant invoice_id inside verify → 404. RLS enforced at DB level.
11. **Scheduler** — `manage.py issue_due_invoices [--date YYYY-MM-DD] [--tenant NAMESPACE] [--dry-run]` (management/commands/issue_due_invoices.py). Runs per active tenant using the **tenant timezone** (WIB/WITA/WIT). Eligible services: `lifecycle=provisioned`, active billing package, `start_date` set. `--dry-run` prints `[DRY] <ns> <svc>: prepaid #0 2026-12-01..2027-01-01`. **Not exposed via API** — a dashboard cannot query scheduler status (Gap G-9).

---

## 6. Test fixture recipes

Auth pattern (all billing tests): `CsrfAPIClient` seeds CSRF via `GET /api/v1/auth/session`, then `force_login(user)` + session `active_tenant_id` + `auth_at` (`tests/conftest.py:64-112`). `tenant_a` fixture = owner + namespace `rtrw-aaaa000001` (conftest.py:79-85).

### Recipe A — ORM: package → invoice → record → verify → receipt (from `test_billing_payments.py:47-77, 96-115, 186-204, 331-351`)

```python
from datetime import date
from decimal import Decimal
import base64

with tenant_scope(tenant_a.id):
    customer = Customer.objects.create(
        tenant=tenant_a, display_name="Ibu Wati", customer_code="CUST-PAY1")
    package = BillingPackage.objects.create(
        tenant=tenant_a, name="Paket Bayar", monthly_price=Decimal("300000"))
    service = Service.objects.create(
        tenant=tenant_a, customer=customer, service_code="SVC-PAY1",
        lifecycle=Service.Lifecycle.PROVISIONED,
        start_date=date(2026, 12, 1), billing_package=package)
    invoice = InternetInvoice.objects.create(
        tenant=tenant_a, service=service, kind="prepaid",
        state=InternetInvoice.State.OPEN, period_index=0,
        period_start=date(2026, 12, 1), period_end=date(2027, 1, 1),
        doc_number=f"INV-{tenant_a.namespace}-202611-0001",
        total_amount=Decimal("300000.00"), due_date=date(2026, 12, 1))

# record (payments_admin session; proof required for transfer)
record = client.post(f"/api/v1/tenants/{t.id}/payments",
    {"method": "cash", "amount": "300000"},
    headers={"Idempotency-Key": "pay-1"}).json()

# verify with allocation
verify = client.post(f"/api/v1/tenants/{t.id}/payments/{record['id']}/verify",
    {"allocations": [{"invoice_id": invoice.id, "amount": "300000"}]},
    headers={"Idempotency-Key": "ver-1"})
assert verify.json()["state"] == "verified" and verify.json()["credit"] == "0.00"

# receipt lookup
docs = client.get(f"/api/v1/tenants/{t.id}/documents"
                  f"?kind=receipt&ref_type=billing_payment&ref_id={record['id']}").json()["items"]
receipt = docs[0]  # doc_number startswith "RCP-"
pdf = client.get(f"/api/v1/tenants/{t.id}/documents/{receipt['id']}")
assert pdf.headers["Content-Type"].startswith("application/pdf")

# proof bytes for bank transfer:
png_b64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode()
```

### Recipe B — scheduler-issued invoice (from `test_billing_invoice_flow.py:43-68, 65-68`)

```python
from io import StringIO
from django.core.management import call_command

buf = StringIO()
call_command("issue_due_invoices", "--tenant", tenant.namespace,
             "--date", "2026-11-24", stdout=buf, stderr=StringIO())
# prepaid start 2026-12-01 → issue 2026-11-24 (start-7), due 2026-12-01, total 300000.00
```

### Recipe C — role sessions (`test_billing_payments.py:80-93`)

```python
admin = User.objects.create_user(email="payadmin@test.local", full_name="Admin Bayar",
                                 password=TEST_PASSWORD, is_active=True)
Membership.objects.create(user=admin, tenant_id=tenant_a.id, role=Role.PAYMENTS_ADMIN)
client.force_login(admin)
session = client.session
session["active_tenant_id"] = str(tenant_a.id)
session["auth_at"] = time.time()
session.save()
```

Exact response fields asserted in tests: `items[0]["outstanding"] == "300000.00"`, `items[0]["document_id"]`, `detail["lines"][0]["line_kind"] == "subscription"` (test_billing_invoice_flow.py:371-383); `body["state"]`, `body["credit"]`, `body["allocated_amount"] == "0.00"` (test_billing_payments.py:113-115, 366-368); aging `body["as_of"]`, `totals["current"]["outstanding"] == "300000.00"` (test_billing_payments.py:458-478); error codes `billing.invalid_policy`, `idempotency_conflict`, `billing.payment_decided`, `billing.allocation_exceeds_payment`, `billing.allocation_exceeds_outstanding`, `billing.invoice_not_payable`, `not_found`, `validation_error`.

---

## 7. Gaps / notes for TK-604

| # | Gap | Detail / workaround |
|---|-----|---------------------|
| G-1 | **`cursor` ignored on `/invoices` and `/payments` GET** | `billing/views.py:_paginate` (149-158) and payment list (374-381) build `next_cursor` but never decode a `cursor` param (documents list *does*, documents/views.py:36-39). UI can only render the first page (max 200 via `limit`). Either fix backend in TK-604 or cap UI at one page. |
| G-2 | **No customer/service context on payments** | `InternetPayment` has no service/customer FK (models.py:251-280); `payment_info` exposes none. The "Pengajuan pembayaran" tab can only show method/amount/external_ref/collector/has_proof/time. Customer linkage appears only post-verify via allocations → invoice. UI must not pretend to show "pelanggan" for submitted payments. |
| G-3 | **No proof viewer endpoint** | Only `has_proof: bool`. UI_UX §8 requires "Bukti transfer dapat diperbesar oleh role berwenang" — needs a new endpoint (e.g. `GET /payments/{id}/proof`) or defer with honest messaging. |
| G-4 | **Receipt id not in `payment_info`** | Two-step lookup: `GET /documents?kind=receipt&ref_type=billing_payment&ref_id={payment_id}` → `items[0].id` → PDF URL. Consider backend addition later. |
| G-5 | **No `/meta/enums` labels for billing enums** | Invoice state, payment state/method, aging buckets, package cycle/timing/policy, charge kinds are absent from `domains/i18n/enums.py:8-52`. Hardcode localized labels in frontend constants (id/en). |
| G-6 | **Invoice filters** | `state` is single-valued (no `open,partial` multi-select server-side); no customer-name/service-code text search (only exact `service_id`); `period_from`/`period_to` exist (UI_UX: "Periode filter selalu terlihat" ✅). For "payable invoices" picker in the verify dialog: 2 requests (`state=open`, `state=partial`) or client-side filter. |
| G-7 | **Payment list filters** | Only `state` + `method` + `limit`. No date-range, no service/customer filter. |
| G-8 | **No activation API (U10)** | No `POST /services/{id}/activate`, no bulk activation, no eligibility endpoint; `quick_tab=paid_awaiting_activation` intentionally empty (customers/views.py:260-261); `activate_service` job kind exists but nothing enqueues it. Only `PATCH /access-accounts/{id}` (suspended→active, perm `services.activate`, 204). U10 must be honest per UI_UX §8: build eligibility client-side (paid invoices × service/account state), label router-not-`Otoritatif` caveat, and treat actual activation as the account-state PATCH or "belum tersedia". |
| G-9 | **Scheduler not queryable via API** | `issue_due_invoices` is a management command only (systemd timer 01:00 planned). Dashboards can't show last-run; show nothing or static copy. |
| G-10 | **No invoice void / refund flow** | `void` state + `void_reason`/`voided_at` fields exist but no API sets them; payment reject has no correction doc. UI should not offer void/refund buttons. |
| G-11 | **No totals in page envelope** | `{items, next_cursor}` only — no count. Use `/invoices/aging` totals for open/partial summaries (it has count+outstanding per bucket). |
| G-12 | **PDF is a binary response** | `GET /documents/{id}` returns `application/pdf`, not JSON — frontend must use `fetch` → blob / open in new tab, not the JSON `http` helper. |
| G-13 | **Amounts are strings** | All money fields are `"123.00"`-style strings; parse with decimal-safe handling (no float math). |
| G-14 | **Idempotency-Key mandatory on all billing mutations** | Use existing `withIdem()` helper (`apps/web/src/api/live/adapter.ts:60-66`); note same key + changed body → `409 idempotency_conflict` (regenerate key when the user edits a form and resubmits). |
| G-15 | **No billing/activation feature folders exist yet in frontend** | `apps/web/src/features/` has no `billing`/`activation`; routes in `App.tsx` end at existing pages; `LiveApiClient` has no billing methods yet — add `listInvoices/getInvoice/aging/listPayments/recordPayment/verify/reject/listDocuments(+PDF)` following the `/tenants/{t}/...` + `CursorPage` conventions. Mock adapter has no billing fixtures either. |

### Response-envelope cheat sheet for the frontend

- Lists with pagination → `CursorPage<T>` = `{items: T[], next_cursor: string|null}` (invoices, payments, documents).
- Plain arrays (no envelope) → packages list, charges list.
- Single objects → `package_info`, `charge_info`, `invoice_info(+lines)`, `payment_info(+allocations)`.
- Errors → `ApiErrorEnvelope` `{code, message, request_id, locale, field_errors?, retryable?}`; HTTP statuses: 401 anon, 404 non-member/missing, 403 member-without-perm, 422 validation, 409 domain conflicts.
- Mutations: JSON body, `x-csrf-token` + `Idempotency-Key` headers; 201 for creates, 200 for verify/reject/updates, 204 for access-account PATCH.
