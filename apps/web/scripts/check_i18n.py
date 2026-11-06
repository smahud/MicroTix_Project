#!/usr/bin/env python3
"""Ekstraksi kunci pesan dari sumber frontend MicroTix.

Sumber kebenaran pesan: locales/id/web.json (I18N.md §6).
Memindai t('key'), t(`prefix.${var}`), formatMessage({id:'key'}).
Template literal di-expand dengan enumerasi manual.
Exit 1 bila ada kunci hilang / paritas placeholder rusak.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # apps/web
SRC = ROOT / 'src'
ID_CATALOG = ROOT.parent.parent / 'locales' / 'id' / 'web.json'
EN_CATALOG = ROOT.parent.parent / 'locales' / 'en' / 'web.json'

literal_re = re.compile(r"""(?:\bt\(|formatMessage\(\{\s*id:\s*)['"]([a-zA-Z0-9_.]+)['"]""")
template_re = re.compile(r'\bt\(\s*`([^`]*\$\{[^`]*)`')

comment_re = re.compile(r'//[^\n]*|/\*.*?\*/', re.S)

# Template prefix → nilai yang mungkin (dari kode sumber)
ENUM_VALUES = {
    'enums.job_state.': ['queued','claimed','preflight','executing','verifying','waiting_dependency','retry_wait','uncertain','recovery_required','succeeded','failed','cancelled'],
    'enums.connection.': ['online','offline','unknown'],
    'enums.isolation.': ['normal','isolated','awaiting_verification','hold'],
    'enums.payment.': ['unbilled','partial','paid','not_billed'],
    'enums.job_dimension.': ['none','queued','running','needs_review'],
    'enums.lifecycle.': ['draft','pending','provisioning','provisioned','conflict','failed','terminated','archived'],
    'enums.enforcement_mode.': ['local','radius_shadow','radius_authoritative','degraded'],
    'enums.monitor_group.': ['healthy','disturbed','unmonitored','stale_data','management_unreachable'],
    'enums.account_state.': ['active','suspended','disabled','expired'],
    'enums.credential_state.': ['unknown','ready','rotation_pending'],
    'enums.invoice_state.': ['draft','open','partial','paid','void'],
    'enums.payment_state.': ['submitted','verified','rejected'],
    'enums.payment_method.': ['cash','bank_transfer','ewallet','collector_cash'],
    'enums.aging_bucket.': ['not_due','current','d31_60','d61_90','d90_plus'],
    'activation.result_': ['success','changed','failed'],
    'enums.backup_category.': ['routine','manual','pre_change'],
    'enums.backup_state.': ['scheduled','creating','transferring','verifying','committed','expired','failed','abandoned','staging'],
    'enums.submission_state.': ['submitted','reviewing','approved','revision_requested','rejected'],
    'enums.subscription_state.': ['free','pending','active','grace','restricted','ended'],
    'enums.discovery_state.': ['discovered','selected','adopted','ignored','conflict','stale'],
    'enums.service.': ['pppoe','hotspot','any'],
    'enums.radius_client.': ['ok','missing_client','degraded'],
    'enums.vpn.': ['up','down','unknown'],
    'enums.api.': ['up','down','unknown'],
    'job.kind.': ['discover_router','harvest_passwords','commit_migration','radius_cutover_step','disconnect_session','apply_account_attributes','suspend_service','activate_service','backup_router','import_commit','router_release','router_replace','change_plan'],
    'enums.job_phase.': ['queued','connect','read_sources','build_snapshot','commit','reserve','create_account','verify','transfer','export','temp_account','read_creds','cleanup','verify_cleanup','fence','detach','slot','cutover_hint','preflight','install_client','shadow','authoritative','apply','disconnect'],
    'role.': ['owner','technician','payments_admin','accountant','viewer','collector','agent'],
    'landing.plan_': ['free','bronze','silver','gold','diamond','platinum'],
    'customers.choice_': ['draft','link_existing','create_account','create_and_activate'],
    'imports.resolution_': ['merge','keep_one','rename'],
    'imports.step_': ['source','select','identity','map_customers','map_profiles','password','review','save'],
    'imports.pw_': ['harvest_temporary','csv','new_password','radius_import','unknown'],
    'imports.csv_mode_': ['create','link','update','device_mapping','password_migration'],
    'imports.conflict_kind_': ['structural_match','password_conflict'],
    'routers.stage_': ['vpn_handshake','api_verify','auth_permission','compatibility'],
    'routers.cap_': ['pppoe','hotspot','radius_client','fasttrack_detect'],
    'routers.radius_client_': ['missing_client','degraded'],
    'monitoring.group_': ['healthy','disturbed','unmonitored','stale_data','management_unreachable'],
    'overview.onboard_': ['company','router','adopt','map','billing','team'],
    'validation.csv_': ['required','email','min_length','pattern','max_rows','max_size','mime','ip_prefix'],
    'radius.cutover_': [f'b{i}' for i in range(7)],
    'landing.benefit_': ['adopt', 'customers', 'radius', 'backup'],
}

# Kunci yang dirujuk lewat objek konfigurasi (bukan pemanggilan t() literal) —
# mis. NAV_GROUPS di AppShell memakai labelKey string.
DYNAMIC_KEYS = {
    'nav.group.operational', 'nav.group.network', 'nav.group.finance', 'nav.group.company', 'nav.group.help',
    'nav.overview', 'nav.customers', 'nav.packages', 'nav.billing', 'nav.incidents', 'nav.jobs',
    'nav.routers', 'nav.radius', 'nav.backups', 'nav.devices', 'nav.inventory', 'nav.configuration',
    'nav.finance', 'nav.team', 'nav.subscription', 'nav.help', 'nav.main_nav',
    'job.kind.discover_router',  # contoh: job kind dipakai dinamis penuh
}

keys = set()
templates = set()

for f in SRC.rglob('*.ts*'):
    text = comment_re.sub('', f.read_text(encoding='utf-8'))
    for m in literal_re.finditer(text):
        keys.add(m.group(1))
    for m in template_re.finditer(text):
        templates.add(m.group(1))

unresolved = []
for tpl in templates:
    # Pecah template `prefix${...}suffix` — satu variabel per template.
    head, _, rest = tpl.partition('${')
    brace_end = rest.find('}')
    suffix = rest[brace_end + 1:] if brace_end >= 0 else ''
    prefix = head
    vals = ENUM_VALUES.get(prefix)
    if vals:
        for v in vals:
            keys.add(prefix + v + suffix)
    else:
        unresolved.append(tpl)
keys.update(DYNAMIC_KEYS)

# EnumBadge / useEnumLabel dinamis: sertakan seluruh enums.*
for group, vals in ENUM_VALUES.items():
    if group.startswith('enums.'):
        keys.update(group + v for v in vals)
idc = json.loads(ID_CATALOG.read_text(encoding='utf-8'))
enc = json.loads(EN_CATALOG.read_text(encoding='utf-8'))

missing_id = sorted(k for k in keys if k not in idc)
missing_en = sorted(k for k in keys if k not in enc)
extra_id = sorted(k for k in idc if k not in keys)

print(f'Keys used (literal+expanded): {len(keys)}')
print(f'id catalog: {len(idc)}; en catalog: {len(enc)}')
for u in unresolved:
    print(f'TEMPLATE-UNRESOLVED: {u}')
print(f'Missing in id: {len(missing_id)}')
for k in missing_id:
    print(f'  ID-MISSING {k}')
print(f'Missing in en: {len(missing_en)}')
for k in missing_en:
    print(f'  EN-MISSING {k}')
print(f'Extra in id (unused): {len(extra_id)}')
for k in extra_id[:300]:
    print(f'  ID-EXTRA {k}')

# Paritas placeholder — buang klausa plural/select ICU lebih dulu
plural_re = re.compile(r'\{\s*[a-zA-Z0-9_]+\s*,\s*(?:plural|select|selectordinal)\s*,.*?\}\s*\}', re.S)
ph_re = re.compile(r'\{([a-zA-Z0-9_]+)[,}]')

def placeholders(s: str) -> set[str]:
    cleaned = plural_re.sub('', str(s))
    return set(ph_re.findall(cleaned))

ph_errors = []
for k in keys:
    if k in idc and k in enc:
        a, b = placeholders(idc[k]), placeholders(enc[k])
        if a != b:
            ph_errors.append(f'{k}: id={sorted(a)} en={sorted(b)}')
if ph_errors:
    print('Placeholder mismatch:')
    for e in ph_errors:
        print(f'  {e}')
else:
    print('Placeholder parity: OK')

# Terjemahan identik (mungkin disengaja untuk istilah teknis) — hanya info
same = [k for k in keys if k in idc and k in enc and idc[k] == enc[k]]
print(f'Identical id/en (info): {len(same)}')

sys.exit(1 if (missing_id or missing_en or ph_errors or unresolved or extra_id) else 0)
