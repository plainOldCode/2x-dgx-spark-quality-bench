from __future__ import annotations
import json, os, re, shutil, subprocess, tempfile, time, uuid
from pathlib import Path
from .common import ROOT,equivalent,strict_loads

IMAGES={'python':'qbench-python:1','sql':'qbench-python:1','typescript':'qbench-typescript:1'}

class SandboxUnavailable(RuntimeError): pass

def preflight(runtimes):
    if not shutil.which('docker'): raise SandboxUnavailable('Docker is required. Model code is NEVER executed directly on the host.')
    images={}
    for rt in sorted(set(runtimes)):
        image=IMAGES[rt]
        try: p=subprocess.run(['docker','image','inspect',image,'--format','{{.Id}}'],capture_output=True,text=True,timeout=15)
        except (OSError,subprocess.TimeoutExpired) as e: raise SandboxUnavailable(str(e)) from e
        if p.returncode: raise SandboxUnavailable(f'Missing/inaccessible {image}. Run python -m qbench build-sandboxes first.\n{p.stderr[:500]}')
        images[rt]=p.stdout.strip()
    return images

def extract_source(text):
    s=text.strip(); fenced=False
    if s.startswith('```'):
        m=re.fullmatch(r'```[A-Za-z0-9_+.-]*\s*\n(.*?)\n```',s,re.S)
        if not m: return None,False
        s=m.group(1);fenced=True
    return s,fenced

def judge_outputs(stdout,returncode,cases):
    if returncode!=0: return {'passed':False,'score':0.0,'reason':'execution_or_compile_failure','returncode':returncode}
    lines=stdout.splitlines()
    if len(lines)!=len(cases): return {'passed':False,'score':0.0,'reason':'output_count_mismatch','expected_lines':len(cases),'actual_lines':len(lines)}
    results=[]
    for i,(line,c) in enumerate(zip(lines,cases)):
        try:
            r=strict_loads(line)
            ok=r.get('ok') is True and r.get('mutated') is False and equivalent(r.get('value'),c['expected'])
            results.append({'case':i,'passed':ok,'error':r.get('error'), 'mutated':r.get('mutated')})
        except (ValueError,AttributeError): results.append({'case':i,'passed':False,'error':'invalid_output'})
    n=sum(r['passed'] for r in results)
    return {'passed':n==len(cases),'score':n/len(cases),'reason':'ok' if n==len(cases) else 'test_failure','tests_passed':n,'tests_total':len(cases),'cases':results}

def run_code(text,oracle,timeout=30):
    source,fenced=extract_source(text)
    if source is None: return {'passed':False,'score':0.0,'reason':'invalid_code_artifact'}
    runtime=oracle['runtime']; image=IMAGES[runtime]; cid='qbench-'+uuid.uuid4().hex
    ext={'python':'py','typescript':'ts','sql':'sql'}[runtime]
    with tempfile.TemporaryDirectory(prefix='qbench-') as d:
        p=Path(d);p.chmod(0o755)
        (p/f'solution.{ext}').write_text(source,encoding='utf-8')
        (p/'inputs.json').write_text(json.dumps([c['input'] for c in oracle['cases']],ensure_ascii=False),encoding='utf-8')
        harness={'python':'py_harness.py','sql':'sql_harness.py','typescript':'ts_harness.cjs'}[runtime]
        shutil.copy(ROOT/'sandbox'/harness,p/harness)
        for file in p.iterdir(): file.chmod(0o644)
        command=['docker','run','--rm','--pull=never','--name',cid,'--network=none','--read-only',
                 '--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=64','--memory=512m',
                 '--memory-swap=512m','--cpus=1','--ulimit','nofile=128:128','--user','65534:65534',
                 '--tmpfs','/tmp:rw,nosuid,nodev,size=128m','--mount',f'type=bind,src={p},dst=/work,readonly',
                 '--workdir','/tmp',image]
        if runtime=='typescript':
            command+=['sh','-c','tsc /work/solution.ts --strict --target ES2020 --module commonjs --outDir /tmp/build && node /work/ts_harness.cjs /tmp/build/solution.js /work/inputs.json']
        else:
            command+=['python','-B',f'/work/{harness}',f'/work/solution.{ext}','/work/inputs.json']
        reason=None; code=0
        # stdout/stderr are bounded by a watchdog, not buffered without a limit in RAM.
        with tempfile.TemporaryFile() as so,tempfile.TemporaryFile() as se:
            proc=subprocess.Popen(command,stdout=so,stderr=se)
            start=time.monotonic()
            try:
                while proc.poll() is None:
                    if time.monotonic()-start>timeout: reason='sandbox_timeout';break
                    if os.fstat(so.fileno()).st_size+os.fstat(se.fileno()).st_size>4*1024*1024: reason='sandbox_output_limit';break
                    time.sleep(0.05)
                if reason:
                    subprocess.run(['docker','rm','-f',cid],capture_output=True,timeout=10)
                    proc.kill()
                code=proc.wait(timeout=10)
            finally:
                subprocess.run(['docker','rm','-f',cid],capture_output=True,timeout=10)
                if proc.poll() is None: proc.kill();proc.wait()
            so.seek(0);se.seek(0)
            stdout=so.read(4*1024*1024).decode('utf-8','replace');stderr=se.read(8192).decode('utf-8','replace')
        if code==125 and not reason: raise SandboxUnavailable(stderr)
        result={'passed':False,'score':0.0,'reason':reason} if reason else judge_outputs(stdout,code,oracle['cases'])
        result.update(stderr=stderr,artifact_format_compliant=not fenced)
        return result
