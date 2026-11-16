"""Read-only grammar probe from exact candidate migration source, no database."""
import ast
import json
from pathlib import Path
import uuid

root=Path(__file__).resolve().parents[3]
source=root/'backend/domains/jobs/migrations/0004_idempotency_identity.py'
tree=ast.parse(source.read_text())
selected=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'_canonical_uuid','_seg_is_urn','_split_legacy_scope'}],type_ignores=[])
ns={'_uuid':uuid}
exec(compile(selected,str(source),'exec'),ns)
value='abcdef12-2345-6789-abcd-ef1234567890'
other='fedcba98-7654-3210-abcd-ef1234567890'
spellings={'canonical':value,'upper':value.upper(),'compact':uuid.UUID(value).hex,'braced':'{'+value+'}','urn':'urn:uuid:'+value,'braced_urn':'{urn:uuid:'+value+'}','uuid_only':'uuid:'+value,'urn_only':'urn:'+value,'repeat_uuid':'urn:uuid:uuid:'+value,'repeat_urn':'urn:urn:uuid:'+value}
rows=[]
for label,spelling in spellings.items():
    accepted=str(uuid.UUID(spelling))==value
    for where in ('tenant','resource'):
        scope=f'payment_submission:{spelling}:' if where=='tenant' else f'router_backup:{other}:{spelling}'
        parts=ns['_split_legacy_scope'](scope)
        tenant=ns['_canonical_uuid'](parts[1]) if parts else None
        resource=ns['_canonical_uuid'](parts[2]) if parts and parts[2] else ''
        matched=bool(parts) and ((tenant==value and resource=='') if where=='tenant' else (tenant==other and resource==value))
        rows.append({'spelling':label,'position':where,'baseline_uuid_accepts':accepted,'parsed':parts,'canonical_identity_matches':matched})
print(json.dumps({'candidate':'634da4224f15dd6a5a4e9010fe1811dec8c7954d','rows':rows},indent=2))
assert all(row['baseline_uuid_accepts'] for row in rows)
assert sum(not row['canonical_identity_matches'] for row in rows)==8
