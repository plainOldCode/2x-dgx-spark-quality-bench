from copy import deepcopy
def solve(data):
    def merge(t,p):
        if not isinstance(p,dict): return deepcopy(p)
        t=deepcopy(t) if isinstance(t,dict) else {}
        for k,v in p.items():
            if v is None: t.pop(k,None)
            else: t[k]=merge(t.get(k),v)
        return t
    return merge(data['target'], data['patch'])
