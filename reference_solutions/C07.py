def solve(data):
    rows=sorted(data['rows'],key=lambda r:(-r['updated'],r['id']))
    cur=data['cursor']
    if cur is not None: rows=[r for r in rows if (-r['updated'],r['id']) > (-cur[0],cur[1])]
    page=rows[:data['limit']]
    return {'ids':[r['id'] for r in page], 'next_cursor':[page[-1]['updated'],page[-1]['id']] if len(rows)>len(page) and page else None}
