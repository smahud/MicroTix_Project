#!/usr/bin/env python3
"""Print a task-scoped reading map. Does not execute tasks or modify source."""
import argparse,json,sys
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--task',required=True);a=p.parse_args()
 try:
  registry=json.loads((a.root/'agent/task-contracts_v2_1.json').read_text());task=next(t for t in registry['tasks'] if t['task_id']==a.task)
  trace=json.loads((a.root/'sumber/audit/Requirements_Traceability_Matrix.json').read_text());requirements=[r for r in trace['rows'] if a.task in r['implementation_tasks']]
  paths=sorted({r['business_requirement']['path'] for r in requirements})
  output={'common_controls':registry['common_controls'],'task':task,'requirement_locators':[{'id':r['requirement_id'],'source':r['business_requirement'],'assertions':r['assertions'],'release_facets':r['release_facets']} for r in requirements],'source_paths':paths,'read_order':['agent/START_BUILD.md','agent/AGENTS_v2_1.md','master §0–2/§24 plus task-specific amendments','task contract and direct dependency contracts','requirement locators and applicable test specifications'],'execution_started':False,'scope_warning':'This is a reading map, not permission or proof. Normative changes need reviewed authority; formal audit blockers remain explicit.'}
  print(json.dumps(output,ensure_ascii=False,indent=2));return 0
 except (OSError,ValueError,StopIteration) as e:print(json.dumps({'error':'UNKNOWN_TASK_OR_INVALID_PACKAGE','detail':str(e)}));return 2
if __name__=='__main__':sys.exit(main())
