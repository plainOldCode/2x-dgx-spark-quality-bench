def solve(data):
    jobs={j['id']:j for j in data['jobs']}; done={}; pending=set(jobs)
    while pending:
        ready=sorted(x for x in pending if set(jobs[x]['needs'])<=done.keys())
        if not ready: return {'error':'cycle'}
        for x in ready:
            j=jobs[x]; start=max((done[n]['finish'] for n in j['needs']),default=0)
            done[x]={'id':x,'start':start,'finish':start+j['duration']}; pending.remove(x)
    return {'makespan':max((x['finish'] for x in done.values()),default=0),'timings':[done[x] for x in sorted(done)]}
