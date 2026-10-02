from __future__ import annotations
import concurrent.futures,copy,json,os,random,time,platform
from pathlib import Path
from .client import Client,APIError
from .common import ROOT,canonical,digest,load_jsonl,task_payload,write_json
from .grading import ToolSimulator,final_text

FORBIDDEN={'min_tokens','ignore_eos','response_format','structured_outputs','guided_json','stop','best_of','n','stream','model','messages','tools','tool_choice','max_tokens','max_completion_tokens','seed','chat_template_kwargs'}

def normalized_config(config):
    c=copy.deepcopy(config)
    for key in ('base_url','model','label'):
        if not isinstance(c.get(key),str) or not c[key]: raise ValueError('Missing config field '+key)
    c.setdefault('sampling',{'temperature':0.6,'top_p':0.95,'top_k':20,'min_p':0.0,'presence_penalty':0.0,'frequency_penalty':0.0,'repetition_penalty':1.0})
    if FORBIDDEN.intersection(c['sampling']): raise ValueError('Forbidden sampling keys: '+str(FORBIDDEN.intersection(c['sampling'])))
    c.setdefault('chat_template_kwargs',{'enable_thinking':True})
    c.setdefault('max_total_tokens',262144)
    return c

def response_usage(raws):
    total={'prompt_tokens':0,'completion_tokens':0,'reasoning_tokens':None,'cached_tokens':None}
    all_usage=True
    for r in raws:
        u=r.get('usage')
        if not isinstance(u,dict): all_usage=False; continue
        for k in ('prompt_tokens','completion_tokens'): total[k]+=int(u.get(k) or 0)
        for source,key in [('completion_tokens_details','reasoning_tokens'),('prompt_tokens_details','cached_tokens')]:
            value=(u.get(source) or {}).get(key)
            if isinstance(value,int): total[key]=(total[key] or 0)+value
    if not all_usage: total['prompt_tokens']=None;total['completion_tokens']=None
    # Reasoning is normally a subset of completion tokens. NEVER sum them again.
    return total

def run_one(task,oracle,config,repeat,seed):
    client=Client(config); messages=copy.deepcopy(task['messages']); raws=[]; requests=[]; wall=0.0
    sim=ToolSimulator(oracle) if oracle['kind']=='tool' else None
    answer='';finish=None;error=None;status='ok';parse_note=None;first_tool_s=None
    max_turns=task.get('max_turns',1); max_per_request=int(config.get('max_output_tokens',task['max_output_tokens']))
    # One episode has a total generation budget, not an unlimited budget per tool turn.
    episode_budget=int(config.get('episode_output_budget',max_per_request*2 if sim else max_per_request))
    used=0
    for turn in range(max_turns):
        budget=min(max_per_request,episode_budget-used)
        if budget<=0: status='generation_truncated';finish='episode_budget';break
        body={'model':config['model'],'messages':messages,'max_tokens':budget,'stream':False,'seed':seed,
              **config['sampling'],'chat_template_kwargs':config['chat_template_kwargs']}
        if task.get('tools'): body.update(tools=task['tools'],tool_choice='auto')
        # No gold outputs, simulator stage definitions, refs, tests, or context_spec enter this body.
        requests.append(copy.deepcopy(body))
        request_started=time.perf_counter(); recorded_elapsed=False
        try:
            raw,elapsed=client.chat(body);wall+=elapsed;recorded_elapsed=True;raws.append(raw)
            choice=raw['choices'][0];msg=choice['message'];finish=choice.get('finish_reason')
        except (APIError,KeyError,IndexError,TypeError) as e:
            if not recorded_elapsed: wall+=time.perf_counter()-request_started
            status='api_error';error=str(e);break
        reported_tokens=(raw.get('usage') or {}).get('completion_tokens')
        if sim is not None and (not isinstance(reported_tokens,int) or reported_tokens<0):
            status='api_error';error='Missing completion token usage: cannot enforce tool episode budget';break
        used+=reported_tokens if isinstance(reported_tokens,int) and reported_tokens>=0 else budget
        if finish=='length': status='generation_truncated';answer,parse_note=final_text(msg);break
        if finish not in ('stop','tool_calls','function_call'):
            status='unexpected_finish';error=str(finish);answer,parse_note=final_text(msg);break
        calls=msg.get('tool_calls') or []
        if calls:
            if first_tool_s is None: first_tool_s=wall
            if sim is None: status='unexpected_tool_call';error='Tool call on a non-tool task';break
            tool_messages=sim.process(calls)
            if sim.error: status='tool_trace_failure';error=sim.error;break
            # Keep the assistant's reasoning field if supplied; some native templates need it.
            assistant={'role':'assistant','content':msg.get('content'),'tool_calls':calls}
            for key in ('reasoning_content','reasoning'):
                if key in msg: assistant[key]=msg[key]
            messages.append(assistant);messages.extend(tool_messages)
        else:
            answer,parse_note=final_text(msg)
            if sim is not None and not sim.complete: status='tool_trace_failure';error='Final answer before required tool calls'
            if parse_note=='unclosed_think_block': status='parser_error'
            break
    else: status='turn_limit';finish='turn_limit'
    return {'task_id':task['id'],'category':task['category'],'model_label':config['label'],'repeat':repeat,'seed':seed,
            'prompt_sha256':digest({'messages':task['messages'],'tools':task.get('tools',[])}),
            'status':status,'finish_reason':finish,'answer':answer,'parser_note':parse_note,'error':error,
            'tool_trace':sim.trace if sim else [],'tool_trace_complete':sim.complete if sim else None,
            'usage':response_usage(raws),'api_wall_s':wall,'first_tool_response_s':first_tool_s,
            'measured_input_tokens':task.get('measured_input_tokens'),'prepared_target_tokens':task.get('prepared_target_tokens'),
            'request_hashes':[digest(r) for r in requests], 'requests':requests,'responses':raws}

def run_suite(taskfile,configfile,out,*,repeats=1,concurrency=1,seed=1729,categories=None,ids=None,resume=False,include_long=False):
    config=normalized_config(json.loads(Path(configfile).read_text()))
    tasks=load_jsonl(taskfile);oracle=json.loads((ROOT/'tasks/oracles.json').read_text())
    if categories: tasks=[t for t in tasks if t['category'] in categories]
    if ids: tasks=[t for t in tasks if t['id'] in ids]
    if not include_long: tasks=[t for t in tasks if t['category']!='long_context']
    if not tasks: raise ValueError('No selected tasks')
    if repeats<1 or not 1<=concurrency<=4: raise ValueError('repeats >=1, concurrency in 1..4 required')
    if any(t['category']=='long_context' for t in tasks) and concurrency!=1:
        raise ValueError('Long-context lane is intentionally C1-only; do not stress 200K x C4 here')
    client=Client(config);models=client.check_model();token_checks=[]
    for t in tasks:
        if t['category']!='long_context': continue
        if t.get('token_count_status')!='measured_vllm_tokenize': raise ValueError(f"{t['id']}: run prepare first; preview is NOT a measured long-context fixture")
        measured=client.tokenize(t['messages'])
        budget=config.get('max_output_tokens',t['max_output_tokens'])
        if measured['count']+budget>config['max_total_tokens']: raise ValueError(f"{t['id']}: input + output budget exceeds context; never truncate prompts silently")
        same_ids=(measured['token_ids_sha256']==t.get('prepared_token_ids_sha256')) if measured['token_ids_sha256'] and t.get('prepared_token_ids_sha256') else None
        token_checks.append({'id':t['id'],**measured,'matches_prepared_token_ids':same_ids})
        if not same_ids: print(f"WARNING {t['id']}: tokenizer/template token IDs differ or are unavailable; recorded for comparison.",flush=True)
    out=Path(out);out.mkdir(parents=True,exist_ok=True); rawdir=out/'raw';rawdir.mkdir(exist_ok=True)
    generation_protocol={'sampling':config['sampling'],'chat_template_kwargs':config['chat_template_kwargs'],
       'max_output_tokens_override':config.get('max_output_tokens'),'episode_output_budget_override':config.get('episode_output_budget'),
       'task_budgets':{t['id']:t['max_output_tokens'] for t in tasks},'concurrency':concurrency,'seed':seed,'repeats':repeats}
    manifest={'config':config,'suite_sha256':digest(tasks),'oracle_sha256':digest(oracle),'generation_protocol':generation_protocol,
       'ids':[t['id'] for t in tasks],'models_response':models,'tokenizer_checks':token_checks,'python':platform.python_version(),
       'measurement':'Non-streaming end-to-end API response time; no TTFT/TPOT or GPU-kernel timing claim.',
       'long_context':include_long,'started_at_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
    manifest_path=out/'manifest.json'; result_path=out/'results.jsonl'
    if manifest_path.exists():
        previous=json.loads(manifest_path.read_text())
        if not resume: raise FileExistsError('Output already has a run; use a new path or --resume')
        for key in ('config','suite_sha256','oracle_sha256','generation_protocol'):
            if previous[key]!=manifest[key]: raise ValueError('Resume manifest mismatch: '+key)
    else: write_json(manifest_path,manifest)
    done=set()
    if result_path.exists():
        if not resume: raise FileExistsError('Results exist')
        for r in load_jsonl(result_path): done.add((r['task_id'],r['repeat']))
    jobs=[]
    for rep in range(repeats):
        ordered=tasks[:];random.Random(seed+rep).shuffle(ordered)
        jobs.extend((t,rep,seed+rep) for t in ordered if (t['id'],rep) not in done)
    started=time.perf_counter()
    with result_path.open('a',encoding='utf-8') as f, concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures={pool.submit(run_one,t,oracle[t['id']],config,r,s):(t,r) for t,r,s in jobs}
        for future in concurrent.futures.as_completed(futures):
            t,rep=futures[future];r=future.result()
            rawname=f"{t['id']}.r{rep}.json";write_json(rawdir/rawname,{'requests':r.pop('requests'),'responses':r.pop('responses')})
            r['raw_file']='raw/'+rawname;f.write(canonical(r)+'\n');f.flush();os.fsync(f.fileno())
            print(f"{config['label']} {t['id']} r{rep}: {r['status']} / {r['api_wall_s']:.2f}s",flush=True)
    write_json(out/'run_session.json',{'new_episodes':len(jobs),'session_wall_s':time.perf_counter()-started,'resumed':resume})
