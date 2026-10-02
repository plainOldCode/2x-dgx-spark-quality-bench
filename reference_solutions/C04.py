import heapq
def solve(data):
    nodes=set(data['nodes']); edges=set(map(tuple,data['edges']))
    if any(a not in nodes or b not in nodes for a,b in edges): return {'error':'unknown_node'}
    deg={x:0 for x in nodes}; adj={x:[] for x in nodes}
    for a,b in edges: adj[a].append(b); deg[b]+=1
    q=[x for x in nodes if deg[x]==0]; heapq.heapify(q); out=[]
    while q:
        x=heapq.heappop(q); out.append(x)
        for y in adj[x]:
            deg[y]-=1
            if deg[y]==0: heapq.heappush(q,y)
    return out if len(out)==len(nodes) else {'error':'cycle'}
