def solve(data):
    capacity=data['capacity']*1000; tokens=capacity; last=0; out=[]
    for r in data['requests']:
        tokens=min(capacity,tokens+(r['t_ms']-last)*data['rate_per_s']); last=r['t_ms']
        ok=tokens>=r['cost']*1000; out.append(ok)
        if ok: tokens-=r['cost']*1000
    return out
