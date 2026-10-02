"""Runs INSIDE an isolated container. Expected answers are not mounted."""
import copy, importlib.util, json, sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('candidate',sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
inputs=json.loads(Path(sys.argv[2]).read_text())
for inp in inputs:
    original=copy.deepcopy(inp)
    try:
        value=module.solve(inp)
        result={'ok':True,'value':value,'mutated':inp!=original}
        print(json.dumps(result,ensure_ascii=False,allow_nan=False),flush=True)
    except BaseException as exc:
        print(json.dumps({'ok':False,'error':type(exc).__name__+': '+str(exc)[:500]}),flush=True)
