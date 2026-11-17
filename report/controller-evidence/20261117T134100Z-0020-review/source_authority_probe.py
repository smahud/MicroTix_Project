import ast
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace as NS, ModuleType

ROOT=Path(__file__).resolve().parents[3]

def extract(path, names, class_name=None):
    tree=ast.parse((ROOT/path).read_text())
    candidates=tree.body
    if class_name:
        candidates=next(x for x in candidates if isinstance(x,ast.ClassDef) and x.name==class_name).body
    funcs=[x for x in candidates if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name in names]
    for f in funcs:
        f.decorator_list=[]
    return compile(ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')],level=0),*funcs],type_ignores=[])),str(path),'exec')

class Rejected(Exception):
    pass
class ApiError:
    not_found=staticmethod(lambda:Rejected('not_found'))
    forbidden=staticmethod(lambda:Rejected('forbidden'))

auth_ns={'engine':NS(authority_requirement=lambda job:'backups.run'), 'ROLE_PERMISSIONS':{'technician':{'backups.run'}},'is_sensitive':lambda p:False,'ApiError':ApiError}
exec(extract('backend/domains/jobs/views.py',{'_require_job_authority'}),auth_ns)
checks=[]
for method in ('GET','POST'):
    request=NS(method=method,mt_membership=NS(role='technician',router_scope=['router-allowed']))
    job=NS(tenant_id='tenant-a',kind='backup_router',router_id='router-denied')
    try:
        auth_ns['_require_job_authority'](NS(in_scope=lambda tenant:True),request,job)
        checks.append({'method':method,'job_router':job.router_id,'membership_scope':request.mt_membership.router_scope,'authority_check':'ALLOWED'})
    except Rejected as e:
        checks.append({'method':method,'authority_check':str(e)})

class Scope:
    depth=0
    @contextmanager
    def scope(self):
        self.depth+=1
        try:yield
        finally:self.depth-=1
ctx=Scope()
ctx.job=NS(router_id='router-denied',tenant_id='tenant-a')
ctx.payload={'rollback':True}
router=NS(id='router-denied',tenant_id='tenant-a',enforcement_mode='radius_authoritative')
run=NS(phase='B3',state='pending_observation',evidence={'B2':{}},router_id=router.id,tenant_id='tenant-a')
run.save=lambda **kwargs:None
calls=[]
class Query:
    def first(self):return run
    def order_by(self,*args):return self
class RouterQuery:
    def first(self):return router
    def update(self,**kwargs):
        router.enforcement_mode=kwargs.get('enforcement_mode',router.enforcement_mode)
        return 1
class Adapter:
    def rollback_radius(self,router,baseline):return NS(changes=[])
    def apply_action(self,router,plan):calls.append({'op':'APPLY','scope_depth':ctx.depth})
    def verify_action(self,router,plan):
        calls.append({'op':'VERIFY','scope_depth':ctx.depth,'verified':False})
        return {'verified':False}
module=ModuleType('adapters.routeros.simulator')
module.RouterOsSimulator=Adapter
sys.modules['adapters.routeros.simulator']=module
phase=NS(B0='B0',B1='B1',B2='B2',B3='B3',B4='B4',B5='B5',B6='B6')
state=NS(FAILED='failed',AUTHORITATIVE='authoritative',ROLLED_BACK='rolled_back')
ns={'CutoverRun':NS(Phase=phase,State=state,objects=NS(filter=lambda **kw:Query())), 'Router':NS(objects=NS(filter=lambda **kw:RouterQuery()),Enforcement=NS(LOCAL='local')), '_router_ctx':lambda r:r, '_ev':lambda r:r.evidence.setdefault(r.phase,{}),'_save':lambda r:None}
exec(extract('backend/domains/radius/handlers.py',{'_b6_rollback'}),ns)
ns['_PHASE_FN']={'B6':ns['_b6_rollback']}
exec(extract('backend/domains/radius/handlers.py',{'_run_phases','verify'},'RadiusCutoverStepHandler'),ns)
result=ns['_run_phases'](NS(),ctx)
verify_result=ns['verify'](NS(),ctx)
print(json.dumps({'http_helper':checks,'rollback_calls':calls,'rollback_result':result,'stored_enforcement_mode':router.enforcement_mode,'stored_evidence':run.evidence,'handler_verify_result':verify_result},indent=2))
