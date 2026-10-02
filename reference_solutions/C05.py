def solve(data):
    state={}
    for e in data['events']:
        if e['id'] not in state or e['version']>=state[e['id']]['version']: state[e['id']]=e
    return [{'id':k,'version':v['version'],'value':v['value']} for k,v in sorted(state.items()) if not v['deleted']]
