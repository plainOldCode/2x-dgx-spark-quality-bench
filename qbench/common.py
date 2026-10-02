from __future__ import annotations
import hashlib, json, math
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]

def canonical(value: Any) -> str:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()

def load_jsonl(path: str | Path) -> list[dict]:
    rows=[]
    for n,line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(),1):
        if not line.strip(): continue
        try: row=json.loads(line)
        except json.JSONDecodeError as e: raise ValueError(f'{path}:{n}: {e}') from e
        if not isinstance(row,dict): raise ValueError(f'{path}:{n}: expected object')
        rows.append(row)
    return rows

def write_json(path: str | Path, value: Any) -> None:
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def strict_loads(text: str) -> Any:
    def pairs(xs):
        out={}
        for k,v in xs:
            if k in out: raise ValueError('duplicate JSON key: '+k)
            out[k]=v
        return out
    def bad(x): raise ValueError('non-finite JSON value: '+x)
    return json.loads(text,object_pairs_hook=pairs,parse_constant=bad)

def equivalent(a: Any,b: Any) -> bool:
    """Order-insensitive objects; strict types; integral JSON floats equal integers.
    Never coerce bools, numeric strings, nulls, or arrays. No precision-losing int->float cast.
    """
    if isinstance(a,bool) or isinstance(b,bool): return type(a) is type(b) and a==b
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        return a==b and (not isinstance(a,float) or math.isfinite(a)) and (not isinstance(b,float) or math.isfinite(b))
    if type(a) is not type(b): return False
    if isinstance(a,dict): return a.keys()==b.keys() and all(equivalent(a[k],b[k]) for k in a)
    if isinstance(a,list): return len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
    return a==b

def task_payload(task: dict) -> dict:
    """Only these fields ever enter model messages. Oracles/specs/refs are excluded."""
    out={'messages':task['messages']}
    if task.get('tools'): out.update(tools=task['tools'],tool_choice='auto')
    return out

def validate_tasks(tasks: list[dict], oracles: dict) -> dict:
    from collections import Counter
    seen=set()
    allowed={'coding','tool','reasoning','instruction','long_context','korean'}
    for t in tasks:
        tid=t['id']
        if tid in seen: raise ValueError('duplicate id '+tid)
        seen.add(tid)
        if t['category'] not in allowed: raise ValueError('bad category '+tid)
        if tid not in oracles: raise ValueError('missing oracle '+tid)
        if not t.get('messages'): raise ValueError('missing messages '+tid)
        if not all(isinstance(m.get('content'),str) for m in t['messages']): raise ValueError('invalid content '+tid)
        if not 1<=t.get('max_output_tokens',0)<=32768: raise ValueError('bad budget '+tid)
        if any(k in t for k in ('expected','oracle','reference_solution')): raise ValueError('oracle leakage '+tid)
        o=oracles[tid]
        if o['kind']=='code' and not o['cases']: raise ValueError('empty code cases '+tid)
        if o['kind']=='tool':
            names={x['function']['name'] for x in t['tools']}
            for stage in o['stages']:
                if any(c['name'] not in names for c in stage): raise ValueError('missing tool definition '+tid)
    return {'tasks':len(tasks),'categories':dict(Counter(t['category'] for t in tasks)),
            'code_cases':sum(len(oracles[t['id']].get('cases',[])) for t in tasks)}
