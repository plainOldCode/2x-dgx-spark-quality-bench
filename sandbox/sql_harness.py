"""Read-only SQLite evaluator; run inside Docker, not on the host for model SQL."""
import json, sqlite3, sys
from pathlib import Path
query=Path(sys.argv[1]).read_text()
fixtures=json.loads(Path(sys.argv[2]).read_text())
for fixture in fixtures:
    db=sqlite3.connect(':memory:')
    try:
        db.executescript(fixture['ddl'])
        for table,rows in fixture['tables'].items():
            if rows: db.executemany('INSERT INTO '+table+' VALUES ('+','.join('?' for _ in rows[0])+')',rows)
        db.commit();db.enable_load_extension(False)
        db.execute('PRAGMA query_only=ON')
        forbidden={sqlite3.SQLITE_ATTACH,sqlite3.SQLITE_DETACH,sqlite3.SQLITE_PRAGMA}
        def auth(action,a,b,c,d):
            if action in forbidden: return sqlite3.SQLITE_DENY
            if action==sqlite3.SQLITE_FUNCTION and str(b).lower() in ('load_extension','writefile','readfile'): return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        db.set_authorizer(auth)
        steps=[0]
        def progress():
            steps[0]+=1
            return 1 if steps[0]>2000 else 0
        db.set_progress_handler(progress,1000)
        values=[list(r) for r in db.execute(query)]
        print(json.dumps({'ok':True,'value':values,'mutated':False},allow_nan=False),flush=True)
    except BaseException as exc:
        print(json.dumps({'ok':False,'error':type(exc).__name__+': '+str(exc)[:500]}),flush=True)
    finally: db.close()
