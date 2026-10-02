def solve(data):
    w=data['weights']; total=data['total_cents']; s=sum(w)
    out=[total*x//s for x in w]; remainder=[total*x%s for x in w]
    for i in sorted(range(len(w)),key=lambda i:(-remainder[i],i))[:total-sum(out)]: out[i]+=1
    return out
