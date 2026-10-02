from __future__ import annotations
import copy,importlib.util,json,os,shutil,subprocess,sys,tempfile,threading,unittest
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from unittest.mock import patch
from qbench.common import ROOT,load_jsonl,validate_tasks,strict_loads,equivalent,digest,task_payload
from qbench.grading import grade_text,checks,ToolSimulator,final_text
from qbench.sandbox import judge_outputs,extract_source,SandboxUnavailable,preflight
from qbench.runner import run_one,run_suite,normalized_config,response_usage
from qbench.report import grade_run,compare,blind,bootstrap_task_deltas

TASKS=load_jsonl(ROOT/'tasks/core60.jsonl');T={t['id']:t for t in TASKS}
GOLD=json.loads((ROOT/'tasks/oracles.json').read_text())

class Contracts(unittest.TestCase):
    def test_exact_counts(self):
        s=validate_tasks(TASKS,GOLD);self.assertEqual(s['tasks'],60);self.assertEqual(s['code_cases'],166)
        self.assertEqual(s['categories'],{'coding':20,'reasoning':10,'instruction':8,'tool':10,'long_context':8,'korean':4})
    def test_no_oracle_fields_sent(self):
        for t in TASKS:self.assertFalse(set(task_payload(t)) & {'expected','oracle','cases','context_spec','reference'})
    def test_all_noncode_references_pass(self):
        for tid,o in GOLD.items():
            if o['kind']=='code':continue
            text=o.get('reference',o.get('expected'))
            if not isinstance(text,str):text=json.dumps(text,ensure_ascii=False)
            with self.subTest(task=tid):self.assertTrue(grade_text(text,o)['passed'],grade_text(text,o))
    def test_duplicate_json_rejected(self):
        with self.assertRaises(ValueError):strict_loads('{"x":1,"x":1}')
    def test_nan_rejected(self):
        with self.assertRaises(ValueError):strict_loads('{"x":NaN}')
    def test_bool_not_number(self):
        self.assertFalse(equivalent({'x':True},{'x':1}));self.assertTrue(equivalent({'x':1},{'x':1.0}))
        self.assertFalse(equivalent(9007199254740993,9007199254740992.0))
    def test_json_no_lenient_fence(self):
        self.assertFalse(grade_text('```json\n{"name":"ledger"}\n```',GOLD['I02'])['passed'])
    def test_code_fence_extract(self):
        self.assertEqual(extract_source('```python\ndef solve(x): return x\n```'),('def solve(x): return x',True))
        self.assertIsNone(extract_source('```python\nx=1\n```\nextra')[0])
    def test_constraint_failures(self):
        self.assertFalse(grade_text(GOLD['I01']['reference']+'\nextra',GOLD['I01'])['passed'])
        self.assertFalse(grade_text(GOLD['K04']['reference']+' OK',GOLD['K04'])['passed'])
    def test_only_final_content_graded(self):
        self.assertEqual(final_text({'content':None,'reasoning_content':'correct answer'}),('',None))
        self.assertEqual(final_text({'content':'<think>bad</think>42'})[0],'42')
        self.assertEqual(final_text({'content':'<think>answer'})[1],'unclosed_think_block')
    def test_completion_includes_reasoning_not_added_twice(self):
        u=response_usage([{'usage':{'prompt_tokens':10,'completion_tokens':100,'completion_tokens_details':{'reasoning_tokens':80}}}])
        self.assertEqual(u['completion_tokens'],100);self.assertEqual(u['reasoning_tokens'],80)
    def test_sampling_forced_output_rejected(self):
        with self.assertRaises(ValueError):normalized_config({'label':'a','base_url':'http://x','model':'x','sampling':{'ignore_eos':True}})
    def test_code_mutation_rejected(self):
        r=judge_outputs('{"ok":true,"value":[],"mutated":true}\n',0,[{'expected':[]}]);self.assertFalse(r['passed'])
    def test_missing_docker_is_infrastructure_not_model_failure(self):
        with patch('shutil.which',return_value=None):
            with self.assertRaises(SandboxUnavailable):preflight(['python'])
    def test_bootstrap_cluster_not_extra_questions(self):
        self.assertEqual(bootstrap_task_deltas([0,0]),[0,0])
    def test_all_prompt_strings_real(self):
        for t in TASKS:
            self.assertTrue(all(isinstance(m['content'],str) and m['content'] for m in t['messages']))
            self.assertNotIn('{{CONTEXT}}',json.dumps(t))

class ToolTrace(unittest.TestCase):
    @staticmethod
    def raw(c,i=0):return {'id':f'call_{i}','type':'function','function':{'name':c['name'],'arguments':json.dumps(c['arguments'])}}
    def test_valid_all_tool_scenarios(self):
        for tid in (f'T{i:02}' for i in range(1,11)):
            o=GOLD[tid];sim=ToolSimulator(o)
            for i,stage in enumerate(o['stages']):sim.process([self.raw(c,i*10+j) for j,c in enumerate(stage)])
            self.assertTrue(sim.complete,tid)
    def test_parallel_order_flexible(self):
        sim=ToolSimulator(GOLD['T04']);sim.process([self.raw(c,j) for j,c in enumerate(reversed(GOLD['T04']['stages'][0]))]);self.assertTrue(sim.complete)
    def test_sequential_independent_reads(self):
        sim=ToolSimulator(GOLD['T04'])
        for j,c in enumerate(GOLD['T04']['stages'][0]):sim.process([self.raw(c,j)])
        self.assertTrue(sim.complete)
    def test_premature_dependent_call_rejected(self):
        sim=ToolSimulator(GOLD['T01']);sim.process([self.raw(GOLD['T01']['stages'][0][0],0),self.raw(GOLD['T01']['stages'][1][0],1)])
        self.assertIsNotNone(sim.error)
    def test_wrong_args_rejected(self):
        sim=ToolSimulator(GOLD['T02']);c=copy.deepcopy(GOLD['T02']['stages'][0][0]);c['arguments']['name']='other'
        sim.process([self.raw(c)]);self.assertIsNotNone(sim.error)
    def test_unnecessary_call_rejected(self):
        sim=ToolSimulator(GOLD['T05']);sim.process([self.raw(GOLD['T09']['stages'][0][0])]);self.assertIsNotNone(sim.error)

class TrustedReferencePrograms(unittest.TestCase):
    """ONLY bundled, authored references run on the local test host. Never model outputs."""
    pass

def reference_test(tid):
    def test(self):
        o=GOLD[tid];rt=o['runtime'];ext={'python':'py','typescript':'ts','sql':'sql'}[rt]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);src=p/f'solution.{ext}';src.write_text((ROOT/f'reference_solutions/{tid}.{ext}').read_text())
            inp=p/'inputs.json';inp.write_text(json.dumps([c['input'] for c in o['cases']]))
            if rt=='typescript':
                if not shutil.which('node') or not shutil.which('tsc'):self.skipTest('node and tsc required for trusted TS references')
                c=subprocess.run(['tsc',str(src),'--strict','--target','ES2020','--module','commonjs','--outDir',str(p/'build')],capture_output=True,text=True,timeout=25)
                self.assertEqual(c.returncode,0,c.stdout+c.stderr)
                cmd=['node',str(ROOT/'sandbox/ts_harness.cjs'),str(p/'build/solution.js'),str(inp)]
            else:
                harness='py_harness.py' if rt=='python' else 'sql_harness.py'
                cmd=[sys.executable,str(ROOT/'sandbox'/harness),str(src),str(inp)]
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
            grade=judge_outputs(r.stdout,r.returncode,o['cases'])
            self.assertTrue(grade['passed'],(tid,grade,r.stderr))
    return test
for tid in (f'C{i:02}' for i in range(1,21)):setattr(TrustedReferencePrograms,'test_'+tid,reference_test(tid))

class MockHandler(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def send(self,data):
        b=json.dumps(data,ensure_ascii=False).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def do_GET(self):self.send({'data':[{'id':m} for m in ['model-a','model-b','length-model']]})
    def do_POST(self):
        req=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path=='/tokenize':
            count=sum(len(m['content'].split()) for m in req['messages'])+5
            self.send({'count':count,'tokens':list(range(count))});return
        assert not (set(req)&{'expected','oracle','cases','context_spec'})
        task=next(t for t in TASKS if req['messages'][:len(t['messages'])]==t['messages'])
        o=GOLD[task['id']]; content=None;calls=None;finish='stop'
        if o['kind']=='tool':
            done=sum(m.get('role')=='tool' for m in req['messages']);cumulative=0;stage=None
            for s in o['stages']:
                if cumulative==done:stage=s;break
                cumulative+=len(s)
            if stage:
                calls=[{'id':f'call_{done}_{i}','type':'function','function':{'name':c['name'],'arguments':json.dumps(c['arguments'])}} for i,c in enumerate(stage)];finish='tool_calls'
        if not calls:
            value=copy.deepcopy(o.get('expected',o.get('reference')))
            if req['model']=='model-b' and task['id']=='R01':value['queue_at_900']=60001
            content=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
        if req['model']=='length-model':finish='length'
        msg={'role':'assistant','content':content,'reasoning_content':'MOCK ONLY; not a model measurement.'}
        if calls:msg['tool_calls']=calls
        self.send({'choices':[{'message':msg,'finish_reason':finish}],'usage':{'prompt_tokens':100,'completion_tokens':120,'completion_tokens_details':{'reasoning_tokens':80}}})

class MockAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),MockHandler);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def cfg(self,model='model-a'):
        return normalized_config({'label':model,'base_url':f'http://127.0.0.1:{self.server.server_port}/v1','model':model,'timeout_s':10})
    def test_tool_episodes_over_http(self):
        for tid in (f'T{i:02}' for i in range(1,11)):
            r=run_one(T[tid],GOLD[tid],self.cfg(),0,1)
            self.assertEqual(r['status'],'ok',(tid,r));self.assertTrue(r['tool_trace_complete'])
            self.assertTrue(grade_text(r['answer'],GOLD[tid])['passed'])
    def test_cutoff_not_pass(self):
        r=run_one(T['R01'],GOLD['R01'],self.cfg('length-model'),0,1)
        self.assertEqual(r['status'],'generation_truncated')
    def test_run_grade_compare_blind_resume(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);ids=['R01','R02','I01','K01','T01','T04']
            for model in ('model-a','model-b'):
                cf=p/f'{model}.json';cf.write_text(json.dumps(self.cfg(model)))
                out=p/model
                run_suite(ROOT/'tasks/core60.jsonl',cf,out,repeats=2,concurrency=1,ids=ids)
                result=grade_run(out);self.assertEqual(sum(x['episodes'] for x in result.values()),12)
                run_suite(ROOT/'tasks/core60.jsonl',cf,out,repeats=2,concurrency=1,ids=ids,resume=True)
                self.assertEqual(len(load_jsonl(out/'results.jsonl')),12)
            r=compare(p/'model-a',p/'model-b',p/'comparison');self.assertEqual(r['reasoning']['outcomes']['A_only'],2)
            blind(p/'model-a',p/'model-b',p/'blind',limit=3)
            self.assertEqual(len(json.loads((p/'blind/blind_cards.json').read_text())),3)
    def test_mismatched_protocol_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for model in ('model-a','model-b'):
                cf=p/f'{model}.json';cf.write_text(json.dumps(self.cfg(model)))
                run_suite(ROOT/'tasks/core60.jsonl',cf,p/model,ids=['R01']);grade_run(p/model)
            m=p/'model-b/manifest.json';v=json.loads(m.read_text());v['generation_protocol']['seed']=999;m.write_text(json.dumps(v))
            with self.assertRaises(ValueError):compare(p/'model-a',p/'model-b',p/'comparison')
    def test_prepare_measures_not_char_estimates(self):
        from qbench.prepare import prepare
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'frozen.jsonl';prepare(ROOT/'tasks/core60.jsonl',self.cfg(),out,profile='smoke')
            ts=load_jsonl(out)
            for t in ts:
                if t['category']=='long_context':
                    self.assertLessEqual(abs(t['measured_input_tokens']-8192),164)
                    self.assertEqual(t['token_count_status'],'measured_vllm_tokenize')
                    self.assertNotEqual(t['messages'],T[t['id']]['messages'])
    def test_unprepared_long_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);cf=p/'cfg.json';cf.write_text(json.dumps(self.cfg()))
            with self.assertRaises(ValueError):run_suite(ROOT/'tasks/core60.jsonl',cf,p/'out',ids=['L01'],include_long=True)

if __name__=='__main__':unittest.main()
