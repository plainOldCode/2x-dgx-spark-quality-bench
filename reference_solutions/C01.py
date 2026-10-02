def solve(data):
    xs=data['intervals']
    if any(a>b for a,b in xs): return {'error':'invalid_interval'}
    out=[]
    for a,b in sorted((a,b) for a,b in xs if a<b):
        if out and a<=out[-1][1]: out[-1][1]=max(out[-1][1],b)
        else: out.append([a,b])
    return out
