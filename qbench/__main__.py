from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
from .common import ROOT,load_jsonl,validate_tasks,write_json

def comma(s):return [x.strip() for x in s.split(',') if x.strip()] if s else None

def main():
    p=argparse.ArgumentParser(description='Original 60-task checkpoint/deployment regression suite. No server reconfiguration.')
    sub=p.add_subparsers(dest='command',required=True)
    v=sub.add_parser('validate');v.add_argument('--tasks',default=str(ROOT/'tasks/core60.jsonl'))
    t=sub.add_parser('prepare',help='Measure and freeze long inputs using one running server tokenizer; never generates model answers')
    t.add_argument('--tasks',default=str(ROOT/'tasks/core60.jsonl'));t.add_argument('--config',required=True);t.add_argument('--out',required=True)
    t.add_argument('--profile',choices=['smoke','full'],default='smoke');t.add_argument('--seed',type=int,default=20260927)
    r=sub.add_parser('run');r.add_argument('--tasks',default=str(ROOT/'tasks/core60.jsonl'));r.add_argument('--config',required=True);r.add_argument('--out',required=True)
    r.add_argument('--repeats',type=int,default=1);r.add_argument('--concurrency',type=int,default=1);r.add_argument('--seed',type=int,default=1729)
    r.add_argument('--categories');r.add_argument('--ids');r.add_argument('--resume',action='store_true');r.add_argument('--include-long',action='store_true')
    g=sub.add_parser('grade');g.add_argument('--run',required=True);g.add_argument('--non-code-only',action='store_true')
    c=sub.add_parser('compare');c.add_argument('--a',required=True);c.add_argument('--b',required=True);c.add_argument('--out',required=True)
    b=sub.add_parser('blind');b.add_argument('--a',required=True);b.add_argument('--b',required=True);b.add_argument('--out',required=True);b.add_argument('--limit',type=int,default=20)
    sub.add_parser('build-sandboxes',help='Build trusted Python/SQLite and TypeScript judge images; needs Docker/network for this step only')
    sub.add_parser('selftest',help='Run suite tests and trusted reference implementations; never runs model-generated code')
    args=p.parse_args()
    if args.command=='validate':
        summary=validate_tasks(load_jsonl(args.tasks),json.loads((ROOT/'tasks/oracles.json').read_text()))
        print(json.dumps(summary,ensure_ascii=False,indent=2))
    elif args.command=='prepare':
        from .prepare import prepare
        prepare(args.tasks,json.loads(Path(args.config).read_text()),args.out,args.profile,args.seed)
    elif args.command=='run':
        from .runner import run_suite
        run_suite(args.tasks,args.config,args.out,repeats=args.repeats,concurrency=args.concurrency,seed=args.seed,
                  categories=comma(args.categories),ids=comma(args.ids),resume=args.resume,include_long=args.include_long)
    elif args.command=='grade':
        from .report import grade_run
        print(json.dumps(grade_run(args.run,args.non_code_only),indent=2))
    elif args.command=='compare':
        from .report import compare
        print(json.dumps(compare(args.a,args.b,args.out),indent=2))
    elif args.command=='blind':
        from .report import blind
        blind(args.a,args.b,args.out,args.limit)
    elif args.command=='build-sandboxes':
        for rt in ('python','typescript'):
            subprocess.run(['docker','build','--pull','-t',f'qbench-{rt}:1','-f',str(ROOT/f'sandbox/Dockerfile.{rt}'),str(ROOT/'sandbox')],check=True)
    elif args.command=='selftest':
        result=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],cwd=ROOT)
        raise SystemExit(result.returncode)

if __name__=='__main__':
    try: main()
    except (ValueError,FileNotFoundError,FileExistsError,RuntimeError) as e:
        print(f'ERROR: {e}',file=sys.stderr);raise SystemExit(2)
