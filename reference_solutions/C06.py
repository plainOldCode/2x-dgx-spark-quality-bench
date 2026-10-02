def solve(data):
    rs=data['responses']; delays=[]; attempts=0
    for i,r in enumerate(rs[:data['max_attempts']],1):
        attempts=i; status=r['status']
        if status not in {429,500,502,503,504} or i>=data['max_attempts'] or i>=len(rs): break
        delay=min(data['cap_ms'], data['base_ms']*2**(i-1))
        if r.get('retry_after_s') is not None: delay=max(delay,r['retry_after_s']*1000)
        delays.append(delay)
    return {'attempts':attempts,'delays_ms':delays,'last_status':status}
