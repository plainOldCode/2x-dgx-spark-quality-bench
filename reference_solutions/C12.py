from urllib.parse import unquote
def solve(data):
    try: p=unquote(data['path'],encoding='utf-8',errors='strict')
    except UnicodeDecodeError: return {'error':'unsafe_path'}
    if p.startswith('/') or '\x00' in p or '\\' in p: return {'error':'unsafe_path'}
    stack=[]
    for s in p.split('/'):
        if s in ('','.'): continue
        if s=='..':
            if not stack: return {'error':'unsafe_path'}
            stack.pop()
        else: stack.append(s)
    return {'path':'/'.join(stack)} if stack else {'error':'unsafe_path'}
