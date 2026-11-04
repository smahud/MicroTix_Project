#!/usr/bin/env python3
"""Read-only documentation checks. Never connects to targets or executes application tests."""
import argparse,csv,hashlib,io,json,re,sys,ipaddress
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal

def need(ok,reason):
 if not ok:raise ValueError(reason)
def unique(pairs):
 d={}
 for k,v in pairs:need(k not in d,'duplicate JSON key '+k);d[k]=v
 return d
def load(p):return json.loads(Path(p).read_text(),object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite '+x)))
def sha(x):return hashlib.sha256(x).hexdigest()
def dag(d):
 done=set()
 while len(done)<len(d):
  ready={k for k,v in d.items() if k not in done and set(v)<=done}
  need(bool(ready),'dependency cycle/unknown IDs '+str(sorted(set(d)-done)));done|=ready
 return True

def schema_check(v,s,path='$'):
 """Strict validator for the bundled schema vocabulary only; not a general JSON Schema engine."""
 if 'anyOf' in s:
  for a in s['anyOf']:
   try:schema_check(v,a,path);break
   except ValueError:continue
  else:raise ValueError(path+' no anyOf match')
 types={'object':lambda x:type(x) is dict,'array':lambda x:type(x) is list,'string':lambda x:type(x) is str,'integer':lambda x:type(x) is int,'number':lambda x:type(x) in (int,float),'boolean':lambda x:type(x) is bool,'null':lambda x:x is None}
 if 'type' in s:need(types[s['type']](v),path+' type')
 if 'const' in s:need(type(v)==type(s['const']) and v==s['const'],path+' const')
 if 'enum' in s:need(v in s['enum'],path+' enum')
 if isinstance(v,dict):
  need(set(s.get('required',[]))<=set(v),path+' missing fields')
  props=s.get('properties',{});extra=set(v)-set(props);ad=s.get('additionalProperties',True)
  if ad is False:need(not extra,path+' unknown fields '+str(extra))
  for k,val in v.items():
   if k in props:schema_check(val,props[k],path+'.'+k)
   elif isinstance(ad,dict):schema_check(val,ad,path+'.'+k)
 if isinstance(v,list):
  need(len(v)>=s.get('minItems',0),path+' minItems');need(len(v)<=s.get('maxItems',len(v)),path+' maxItems')
  if s.get('uniqueItems'):need(len(v)==len({json.dumps(z,sort_keys=True) for z in v}),path+' duplicate items')
  for i,a in enumerate(v):schema_check(a,s.get('items',{}),path+'['+str(i)+']')
 if isinstance(v,str):
  need(len(v)>=s.get('minLength',0),path+' minLength')
  if 'pattern' in s:need(re.search(s['pattern'],v) is not None,path+' pattern')
  if s.get('format')=='date-time':
   try:d=datetime.fromisoformat(v.replace('Z','+00:00'));need(d.tzinfo is not None,path+' timezone required')
   except (ValueError,TypeError):raise ValueError(path+' RFC3339 datetime')
 if type(v) in (int,float):
  if 'minimum' in s:need(v>=s['minimum'],path+' minimum')
  if 'maximum' in s:need(v<=s['maximum'],path+' maximum')
  if 'exclusiveMinimum' in s:need(v>s['exclusiveMinimum'],path+' exclusiveMinimum')
 for a in s.get('allOf',[]):
  if 'if' in a:
   try:schema_check(v,a['if'],path);condition=True
   except ValueError:condition=False
   if condition:schema_check(v,a.get('then',{}),path)
   else:schema_check(v,a.get('else',{}),path)
  else:schema_check(v,a,path)
 return True

def placeholders(v):
 if isinstance(v,dict):
  for x in v.values():placeholders(x)
 elif isinstance(v,list):
  for x in v:placeholders(x)
 elif isinstance(v,str):need(v.strip().upper() not in ['TBD','CHANGE_ME','TODO','<HOST>','<SECRET>'],'placeholder value')

def validate_profile(p,root):
 schema_check(p,load(root/'sumber/contracts/execution-profile.schema.json'));placeholders(p)
 auth=p['authorization'];need(p['workspace']==auth['workspace'],'workspace outside grant')
 need(Path(p['workspace']).is_absolute(),'workspace must be absolute')
 need(bool(auth['scope_task_ids']),'empty scope')
 start=datetime.fromisoformat(auth['valid_from'].replace('Z','+00:00'));end=datetime.fromisoformat(auth['expires_at'].replace('Z','+00:00'))
 need(start<end,'grant window order');need(start<=datetime.now(timezone.utc)<end,'expired/not-yet-valid window')
 need(p['resource_budget']['run_deadline_s']+p['resource_budget']['cleanup_reserve_s']<=(end-datetime.now(timezone.utc)).total_seconds(),'window shorter than run+cleanup')
 need(p['stage']!='test' or 'local_test' in auth['operations'],'test operation not granted')
 kinds={x['kind'] for x in load(root/'sumber/contracts/job-kind-registry_v2_1.json')['records']}
 need(set(p['kind_deadlines_s'])<=kinds,'unknown deadline kind')
 for k,v in p['kind_deadlines_s'].items():need(v<=p['resource_budget']['run_deadline_s'],'kind exceeds run deadline '+k)
 for b in p['secret_bindings']:need(not re.search(r'(?:password=|token=|secret=|BEGIN PRIVATE KEY)',b['provider_ref'],re.I),'literal secret binding')
 return {'result':'STATIC_INPUT_CHECK_PASSED','runtime_ready':False,'reason':'Factual grant authenticity, files/hashes/resources and secret availability require authorized executor preflight; no network or application run.'}

def validate_targets(v,root):
 schema_check(v,load(root/'sumber/contracts/target-registry.schema.json'));placeholders(v)
 rows=v['records'];ids=[r['target_id'] for r in rows];need(len(set(ids))==len(ids),'duplicate target id');D={r['target_id']:r for r in rows};graph={}
 for r in rows:
  for addr in r['allowed_management_ips']:
   try:ipaddress.ip_address(addr)
   except ValueError:raise ValueError('invalid literal IP '+addr)
  j=r['jump_target_id'];graph[r['target_id']]=[j] if j else []
  if j:need(j in D and D[j]['kind']=='ssh_jump','unknown/wrong jump target');need(D[j]['environment']==r['environment'],'jump environment mismatch')
  for cid in r['compute_target_ids']:need(cid in D and D[cid]['kind']=='gns3_compute','unknown/wrong compute target');need(D[cid]['environment']==r['environment'],'compute environment mismatch')
 dag(graph)
 return {'result':'STATIC_INPUT_CHECK_PASSED','runtime_ready':False,'reason':'File2 actual scope/grant/identity/window and root-target union must be validated before connection; this tool performs no I/O to targets.'}

def verify(root):
 out=[]
 def check(name,ok):need(ok,name);out.append({'check':name,'result':'STATIC_CHECK_PASSED'})
 tr=load(root/'agent/task-contracts_v2_1.json');tasks=tr['tasks'];ids={t['task_id'] for t in tasks}
 check('85 unique source task IDs',len(ids)==len(tasks)==85)
 src=(root/'agent/tugas_v2_1.md').read_text();check('every original task objective retained',all(re.search(r'- \[ \] '+t['task_id']+r'\b',src) for t in tasks))
 required=['objective','scope','prerequisites','required_inputs','authoritative_references','expected_outputs','allowed_modifications','forbidden_actions','dependency_order','acceptance_criteria','test_procedures','error_handling','rollback_recovery','completion_evidence','blocking_conditions']
 check('15 execution contract fields present',all(all(k in t and t[k] is not None for k in required) for t in tasks))
 graph={t['task_id']:[d['task_id'] for d in t['prerequisites']] for t in tasks};check('task dependency closure and DAG',dag(graph))
 order=tr['topological_order'];check('topological order exact IDs',len(order)==85 and set(order)==ids);check('topological order edges',all(order.index(d)<order.index(t) for t,ds in graph.items() for d in ds))
 check('R4 physical profile write',next(t for t in tasks if t['task_id']=='TK-508')['phase']=='P9')
 params=load(root/'sumber/contracts/parameter-registry_v2_1.json')['records'];keys=[p['key'] for p in params];aliases=[a['key'] for p in params for a in p['aliases']]
 check('unique canonical and alias keys',len(keys)==len(set(keys)) and len(aliases)==len(set(aliases)) and not set(keys)&set(aliases))
 for p in params:
  need(all(k in p for k in ['type','unit','default','scope','bounds','classification','source','effective_revision','change_rule']),'parameter metadata '+p['key'])
  if p['type']=='decimal_string':Decimal(p['default']);need(type(p['default']) is str,'decimal encoding')
  if p['type']=='integer':need(type(p['default']) is int,'integer default '+p['key'])
  if p['type']=='boolean':need(type(p['default']) is bool,'bool default')
  if p['type']=='cidr':ipaddress.ip_network(p['default'],strict=True)
 check('typed defaults and metadata',True)
 pd={p['key']:p['default'] for p in params};check('cross-constraints',pd['router.connect_timeout_s']<=pd['router.read_timeout_s']<=pd['router.job_deadline_s'] and pd['job.heartbeat_s']<pd['job.lease_s']/2 and Decimal(pd['backup.warn_ratio'])<Decimal(pd['backup.stop_ratio']))
 kj=load(root/'sumber/contracts/job-kind-registry_v2_1.json')['records'];check('20 unique typed job kinds',len({k['kind'] for k in kj})==len(kj)==20)
 check('every kind bound to source task and deadline',all(k['task_id'] in ids and k['effect_boundary'] and k['verification'] and k['compensation'] and k['deadline_policy']['mode'] in ['registry_default','required_run_input'] for k in kj))
 reg=load(root/'sumber/quality/test-case-registry_v2_1.json');cases=reg['cases'];aids=[a['id'] for c in cases for a in c['assertions_expected']]
 check('84 baseline cases and318 assertions unique',len(cases)==len({c['id'] for c in cases})==84 and len(aids)==len(set(aids))==318)
 blocks=re.findall(r'```json\n(.*?)\n```',(root/'sumber/quality/Test_Case_Specifications_v2_1.md').read_text(),re.S);check('baseline JSON Markdown exact parity',[json.loads(b) for b in blocks]==cases)
 check('baseline all NOT_RUN actual null',all(c['status']=='NOT_RUN' and all(a['result']=='NOT_RUN' and a['actual'] is None for a in c['assertions_expected']) for c in cases))
 cids={c['id'] for c in cases};tokens={'V0','V1','V2','V3','V4','EXECUTION_PROFILE_READY','FIXTURE_READY','FAULT_GRANT_READY','MODEL_CAPABILITY_READY','PRIMARY_SECONDARY_ROUTES_READY','AUTHORITATIVE_FIXTURE_READY'}
 check('case dependency IDs known',all(d in cids|tokens for c in cases for d in c['dependencies']))
 check('case dependency DAG',dag({c['id']:[d for d in c['dependencies'] if d in cids] for c in cases}))
 sp=load(root/'sumber/quality/supplemental-test-registry_v2_1.json');rr=sp['requirement_cases'];trace=load(root/'sumber/audit/Requirements_Traceability_Matrix.json');rows=trace['rows'];rids={r['requirement_id'] for r in rows}
 check('172 unique requirements and targeted scenarios',len(rids)==len(rows)==len(rr)==172 and {c['requirement_ids'][0] for c in rr}==rids)
 check('requirement trace edges concrete',all(r['implementation_tasks'] and set(r['implementation_tasks'])<=ids and len(r['assertions'])==2 and r['acceptance_criteria'] and r['design']['id'] for r in rows))
 for r in rows:
  s=r['business_requirement'];data=(root/s['path']).read_text().splitlines(keepends=True);need(s['locator'] in data[s['line']-1],'source locator '+r['requirement_id']);need(sha(data[s['line']-1].encode())==s['line_sha256'],'source clause drift '+r['requirement_id'])
 check('source locator and line hashes',True)
 check('85 build checks align task acceptance',len(sp['build_acceptance_checks'])==85 and all([a['test_assertion'] for a in t['acceptance_criteria']]==[a['id'] for a in next(x for x in sp['build_acceptance_checks'] if x['task_id']==t['task_id'])['assertions_expected']] for t in tasks))
 check('AUD46 MAC8 EXE8 all mapped',len(sp['amendment_review_checks'])==62 and {a['requirement_id'] for a in sp['amendment_review_checks']}=={f'{prefix}-{i:02}' for prefix,n in [('AUD',46),('MAC',8),('EXE',8)] for i in range(1,n+1)})
 sv=(root/'sumber/quality/asvs/ASVS_5.0.0_en.csv').read_bytes();check('ASVS original source hash',sha(sv)=='98c8fe911b9edb403af8ee05d3ce8201ecac2659e313b053890a62847cdcf680')
 standard=list(csv.DictReader(io.StringIO(sv.decode())));ar=load(root/'sumber/quality/asvs-applicability_v2_1.json')['records'];expected={'v5.0.0-'+r['req_id'][1:] for r in standard if r['L'] in ['1','2']};check('ASVS253 exact L1+L2 ID set',len(ar)==len(expected)==253 and {r['id'] for r in ar}==expected)
 for r in ar:
  source=next(x for x in standard if x['req_id']==r['source']['req_id']);need(sha(source['req_description'].encode())==r['source']['description_sha256'],'ASVS source drift')
 check('ASVS source predicates and NOT_RUN state',all(r['result']=='NOT_RUN' and r['actual'] is None and r['owner_task'] in ids and r['applicability'] in ['APPLICABLE','CONDITIONAL_UNTIL_INVENTORY'] for r in ar))
 ap=load(root/'sumber/quality/release-applicability_v2_1.json');assertions={a['id']:a['expected'] for c in cases+rr for a in c['assertions_expected']};aps=ap['assertions'];check('662 assertion applicability IDs complete',len(aps)==len(assertions)==662 and {a['assertion_id'] for a in aps}==set(assertions));check('applicability source hashes',all(a['expected_sha256']==sha(assertions[a['assertion_id']].encode()) for a in aps))
 check('HA central not edge-gated',all(a['status_by_release']['R1']=='REQUIRED_SCOPED' for a in aps if a['case_id']=='T22-HA-01'))
 master=(root/'MicroTix-File-1-Kontrak-Revisi-Lengkap.md').read_text();gate=(root/'sumber/quality/Quality_Gates_and_Release_Readiness_v2_1.md').read_text();pat=r'<!-- BEGIN MACRO-NORMATIVE-2.1-macro.1 -->(.*?)<!-- END MACRO-NORMATIVE-2.1-macro.1 -->';check('MAC full projection exact',re.search(pat,master,re.S)[1]==re.search(pat,gate,re.S)[1])
 check('cancellation state explicit', '| executing | verifying, uncertain, failed, recovery_required, cancelled hanya menurut EXE-01 |' in master)
 check('ACS uncertainty mapping explicit','### EXE-02' in master and 'device_task_state' in master and 'job_state' in master)
 # Only actual Markdown links; backtick future output paths are not mislabeled missing payloads.
 broken=[]
 for p in root.rglob('*.md'):
  if '.git' in p.parts:continue
  for dest in re.findall(r'(?<!!)\[[^\]\n]+\]\(([^)\s]+)\)',p.read_text()):
   if re.match(r'^[a-z]+:',dest) or dest.startswith('#'):continue
   path=dest.split('#')[0]
   if path and not (p.parent/path).exists():broken.append((str(p.relative_to(root)),dest))
 check('active Markdown links resolve',not broken)
 for sn in ['execution-profile.schema.json','target-registry.schema.json']:
  s=load(root/'sumber/contracts'/sn);check(sn+' strict root',s['additionalProperties'] is False and s['required'])
 check('no runtime PASS forged',all(a['actual'] is None and a['result']=='NOT_RUN' for c in rr for a in c['assertions_expected']))
 return {'result':'STATIC_CHECK_PASSED','scope':'documentation_structures_and_source_parity','checks':out,'check_count':len(out),'runtime_tests_executed':0,'independent_semantic_review':False,'formal_audit_status':'BLOCKED','blockers':['SEC-DEC-01','INDEPENDENT_SEMANTIC_AND_ATOMIC_CLAUSE_REVIEW'],'package_revision':'2.1-build.1'}

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',type=Path,required=True);a.add_argument('--profile',type=Path);a.add_argument('--target-registry',type=Path);args=a.parse_args()
 try:
  result=validate_profile(load(args.profile),args.root) if args.profile else validate_targets(load(args.target_registry),args.root) if args.target_registry else verify(args.root)
  print(json.dumps(result,ensure_ascii=False,indent=2));return 0
 except (ValueError,KeyError,IndexError,OSError,StopIteration) as e:print(json.dumps({'result':'FAIL','scope':'documentation_static','error':str(e)}));return 1
if __name__=='__main__':sys.exit(main())
