from collections import OrderedDict
def solve(data):
    cache=OrderedDict(); out=[]
    for op in data['ops']:
        t=op['t']
        for key in list(cache):
            if cache[key][1]<=t: del cache[key]
        k=op['key']
        if op['op']=='get':
            if k in cache:
                v,_=cache[k]; cache.move_to_end(k); out.append(v)
            else: out.append(None)
        else:
            cache.pop(k,None)
            if op['ttl']>0 and data['capacity']>0:
                cache[k]=(op['value'], t+op['ttl'])
                while len(cache)>data['capacity']: cache.popitem(last=False)
    return out
