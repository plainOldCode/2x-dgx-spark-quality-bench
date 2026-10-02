from __future__ import annotations
import csv,json,math,random,statistics
from pathlib import Path
from collections import defaultdict,Counter
from .common import ROOT,canonical,digest,load_jsonl,write_json
from .grading import grade_text
from .sandbox import preflight,run_code,SandboxUnavailable

def summarize(rows):
    groups=defaultdict(list)
    for r in rows: groups[r['category']].append(r)
    output={}
    for cat,rs in sorted(groups.items()):
        scored=[r for r in rs if r['grade']['passed'] is not None]
        passed=sum(r['grade']['passed'] is True for r in scored)
        times=[r['api_wall_s'] for r in rs if r['status']=='ok']
        solved=[r['api_wall_s'] for r in rs if r['grade']['passed'] is True]
        output[cat]={'episodes':len(rs),'quality_scored':len(scored),'passed':passed,
          'pass_rate':passed/len(scored) if scored else None,'operational_success_rate':passed/len(rs),
          'infrastructure_or_unscored':len(rs)-len(scored),'statuses':dict(Counter(r['status'] for r in rs)),
          'median_response_s':statistics.median(times) if times else None,
          'median_solved_response_s':statistics.median(solved) if solved else None}
    return output

def grade_run(run_dir,non_code_only=False):
    p=Path(run_dir); rows=load_jsonl(p/'results.jsonl');manifest=json.loads((p/'manifest.json').read_text())
    oracles=json.loads((ROOT/'tasks/oracles.json').read_text())
    if manifest['oracle_sha256']!=digest(oracles): raise ValueError('Oracle changed since generation; refuse grading')
    runtimes=[oracles[r['task_id']]['runtime'] for r in rows if oracles[r['task_id']]['kind']=='code' and r['status']=='ok']
    images=preflight(runtimes) if runtimes and not non_code_only else {}
    for r in rows:
        oracle=oracles[r['task_id']]
        if r['status']=='api_error':
            grade={'passed':None,'score':None,'reason':'infrastructure_api_error'}
        elif r['status']!='ok': grade={'passed':False,'score':0.0,'reason':r['status']}
        elif oracle['kind']=='code':
            if non_code_only: grade={'passed':None,'score':None,'reason':'code_grading_explicitly_skipped'}
            else:
                try: grade=run_code(r['answer'],oracle)
                except SandboxUnavailable as e: grade={'passed':None,'score':None,'reason':'infrastructure_sandbox_error','detail':str(e)}
        else: grade=grade_text(r['answer'],oracle)
        r['grade']=grade
    with (p/'graded.jsonl').open('w',encoding='utf-8') as f:
        for r in rows: f.write(canonical(r)+'\n')
    summary=summarize(rows)
    write_json(p/'summary.json',{'categories':summary,'sandbox_image_ids':images,'note':'No combined leaderboard score. API errors are unscored quality but count against operational completion.'})
    lines=['# Regression run summary','',f"Model label: `{manifest['config']['label']}`",'',
       '| Category | Scored / attempted | Pass | Pass rate | Operational success | Median response s |',
       '|---|---:|---:|---:|---:|---:|']
    for cat,s in summary.items():
        percent=lambda n:'N/A' if n is None else f'{n*100:.1f}%'
        timing='N/A' if s['median_response_s'] is None else f"{s['median_response_s']:.2f}"
        lines.append(f"| {cat} | {s['quality_scored']} / {s['episodes']} | {s['passed']} | {percent(s['pass_rate'])} | {percent(s['operational_success_rate'])} | {timing} |")
    lines+=['','A pass requires all mandatory checks. Partial scores are diagnostic only.',
             'Timing is non-streaming end-to-end API time, not TTFT or pure decode speed.',
             'Code compilation/test time is excluded from API timing. Tool tasks include all model calls, but only simulated tool work.',
             'Small category counts cannot establish noninferiority. Inspect per-task regressions and repeat them.']
    (p/'SUMMARY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return summary

def bootstrap_task_deltas(values,seed=271828,n=5000):
    """Resample unique tasks, not repeated generations as independent questions."""
    if not values:return None
    rng=random.Random(seed);samples=[]
    for _ in range(n):samples.append(sum(rng.choice(values) for _ in values)/len(values))
    samples.sort()
    return [samples[int(n*.025)],samples[min(n-1,int(n*.975))]]

def compare(a_dir,b_dir,out):
    a=Path(a_dir);b=Path(b_dir);ma=json.loads((a/'manifest.json').read_text());mb=json.loads((b/'manifest.json').read_text())
    for key in ('suite_sha256','oracle_sha256','generation_protocol'):
        if ma[key]!=mb[key]: raise ValueError(f'Incomparable runs: {key} differs. Use the identical frozen suite, sampling, budgets, repeats and concurrency.')
    ar=load_jsonl(a/'graded.jsonl');br=load_jsonl(b/'graded.jsonl')
    def index(rows):
        d={}
        for r in rows:
            key=(r['task_id'],r['repeat'],r['seed'])
            if key in d: raise ValueError('duplicate result key')
            d[key]=r
        return d
    aa=index(ar);bb=index(br)
    if aa.keys()!=bb.keys(): raise ValueError('Result coverage differs; do not silently drop failures or missing tasks')
    pairs=[];bycat=defaultdict(list)
    for key in sorted(aa):
        x,y=aa[key],bb[key]
        if x['prompt_sha256']!=y['prompt_sha256']: raise ValueError('Prompt mismatch '+key[0])
        ap=x['grade']['passed'];bp=y['grade']['passed']
        label='unscored' if ap is None or bp is None else ('tie_pass' if ap and bp else 'tie_fail' if not ap and not bp else 'A_only' if ap else 'B_only')
        r={'task_id':key[0],'repeat':key[1],'seed':key[2],'category':x['category'],'A_pass':ap,'B_pass':bp,
           'outcome':label,'A_seconds':x['api_wall_s'],'B_seconds':y['api_wall_s'],
           'B_over_A_latency':y['api_wall_s']/x['api_wall_s'] if ap is True and bp is True and x['api_wall_s']>0 else None}
        pairs.append(r);bycat[r['category']].append(r)
    summary={}
    for cat,rs in bycat.items():
        grouped=defaultdict(list)
        for r in rs:
            if r['A_pass'] is not None and r['B_pass'] is not None: grouped[r['task_id']].append(int(r['B_pass'])-int(r['A_pass']))
        deltas=[statistics.mean(v) for v in grouped.values()]
        ratios=[r['B_over_A_latency'] for r in rs if r['B_over_A_latency'] is not None]
        summary[cat]={'paired_episodes':len(rs),'unique_tasks':len({r['task_id'] for r in rs}),
          'outcomes':dict(Counter(r['outcome'] for r in rs)),'mean_task_pass_delta_B_minus_A':statistics.mean(deltas) if deltas else None,
          'task_cluster_bootstrap_95ci':bootstrap_task_deltas(deltas),
          'median_latency_ratio_B_over_A_both_pass':statistics.median(ratios) if ratios else None}
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    write_json(out/'comparison.json',{'A':ma['config']['label'],'B':mb['config']['label'],'categories':summary,
        'A_server_identity':ma['config'].get('server_identity'),'B_server_identity':mb['config'].get('server_identity'),
        'A_tokenizer_checks':ma.get('tokenizer_checks'),'B_tokenizer_checks':mb.get('tokenizer_checks'),
        'warning':'Bootstrap intervals describe this small, original task set only; zero observed differences are NOT proof of equivalent model quality.'})
    with (out/'pairs.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(pairs[0]));w.writeheader();w.writerows(pairs)
    lines=['# Paired comparison','',f"A: `{ma['config']['label']}`; B: `{mb['config']['label']}`",'',
      '| Category | Unique tasks | A only | B only | Both pass | Both fail | Unscored | B−A pass rate |',
      '|---|---:|---:|---:|---:|---:|---:|---:|']
    for cat,s in sorted(summary.items()):
        c=s['outcomes'];d=s['mean_task_pass_delta_B_minus_A'];dt='N/A' if d is None else f'{100*d:+.1f} pp'
        lines.append(f"| {cat} | {s['unique_tasks']} | {c.get('A_only',0)} | {c.get('B_only',0)} | {c.get('tie_pass',0)} | {c.get('tie_fail',0)} | {c.get('unscored',0)} | {dt} |")
    lines+=['','## Interpretation','',
      'Do not infer equality from no observed regressions. One item moves a 20-item category by 5 percentage points.',
      'Review A-only failures first. Compare latency on tasks BOTH pass, and retain all failures in operational totals.',
      'Different kernels, templates, MTP or checkpoint sources make this a deployment comparison, not an isolated quantization experiment.',
      'This package does not measure full repository patching, visual ability, free-form writing quality or multiday OOM stability.',
      'All long-context tasks are synthetic. A successful lookup does not prove broad reasoning at that length.',
      'Blind review can supplement objective grading, not replace executable correctness tests.']
    (out/'COMPARISON.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return summary

def blind(a_dir,b_dir,out,limit=20,seed=314159):
    aa={(r['task_id'],r['repeat']):r for r in load_jsonl(Path(a_dir)/'results.jsonl')}
    bb={(r['task_id'],r['repeat']):r for r in load_jsonl(Path(b_dir)/'results.jsonl')}
    keys=sorted(aa.keys() & bb.keys());rng=random.Random(seed);rng.shuffle(keys);keys=keys[:limit]
    cards=[];keyfile=[]
    for i,k in enumerate(keys,1):
        x,y=aa[k],bb[k]
        if x['prompt_sha256']!=y['prompt_sha256']:raise ValueError('Blind review prompt mismatch')
        order=[('A',x),('B',y)];rng.shuffle(order)
        def raw_question(run_dir,row):
            raw=json.loads((Path(run_dir)/row['raw_file']).read_text())
            # Long fixture is stored in the raw file; use the question after the archive for concise review.
            return raw['requests'][0]['messages'][-1]['content'] if raw['requests'] else '(No request recorded)'
        prompt=raw_question(a_dir,x)
        cards.append({'blind_id':f'B{i:03}','task_id':k[0],'repeat':k[1],'prompt':prompt,
            'output_1':order[0][1]['answer'],'output_2':order[1][1]['answer'],
            'trace_1':order[0][1]['tool_trace'],'trace_2':order[1][1]['tool_trace'],
            'verdict':None,'notes':''})
        keyfile.append({'blind_id':f'B{i:03}','output_1':order[0][0],'output_2':order[1][0]})
    out=Path(out);out.mkdir(parents=True,exist_ok=True);write_json(out/'blind_cards.json',cards);write_json(out/'DO_NOT_SHARE_answer_key.json',keyfile)
