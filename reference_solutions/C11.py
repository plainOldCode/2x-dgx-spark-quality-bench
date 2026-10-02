import csv,io
def solve(data):
    out=[]; seen=set()
    for r in csv.DictReader(io.StringIO(data['csv'],newline='')):
        e=r['email'].strip().lower()
        if r['active'].strip().lower()=='true' and e and e not in seen:
            seen.add(e); out.append({'name':r['name'],'email':e})
    return out
