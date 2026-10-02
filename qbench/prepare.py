from __future__ import annotations
import copy, importlib.util
from pathlib import Path
from .common import ROOT,load_jsonl,write_json,digest
from .client import Client

def prepare(taskfile,config,out,profile='smoke',seed=20260927):
    if Path(out).exists(): raise FileExistsError(f'{out} exists; never overwrite a frozen suite')
    tasks=load_jsonl(taskfile); client=Client(config); client.check_model()
    spec=importlib.util.spec_from_file_location('_suite_builder',ROOT/'scripts/build_suite.py')
    builder=importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    result=[]; measurements=[]
    for task in tasks:
        t=copy.deepcopy(task)
        if t['category']=='long_context':
            target=t['context_spec']['target_input_tokens'] if profile=='full' else 8192
            n=80
            for attempt in range(12):
                messages=builder.long_messages(t['context_spec'],n,seed)
                measured=client.tokenize(messages)
                count=measured['count']
                if abs(count-target)<=max(128,target*0.02): break
                new=max(1,round(n*target/count))
                if new==n: new=n+(1 if count<target else -1)
                n=new
            else: raise RuntimeError(f"Could not size {t['id']} near {target} tokens; got {count}")
            t['messages']=messages; t['measured_input_tokens']=count
            t['token_count_status']='measured_vllm_tokenize'
            t['prepared_token_ids_sha256']=measured['token_ids_sha256']
            t['prepared_chat_template_kwargs']=config.get('chat_template_kwargs',{'enable_thinking':True})
            t['prepared_target_tokens']=target; t['context_seed']=seed
            print(f"{t['id']}: target={target}, measured={count}, filler_records={n}",flush=True)
            measurements.append({'id':t['id'],**measured,'target':target})
        t['prompt_sha256']=digest({'messages':t['messages'],'tools':t.get('tools',[])})
        result.append(t)
    p=Path(out);p.parent.mkdir(parents=True,exist_ok=True)
    import json
    p.write_text(''.join(json.dumps(t,ensure_ascii=False)+'\n' for t in result),encoding='utf-8')
    write_json(str(out)+'.manifest.json',{'suite_sha256':digest(result),'source_sha256':digest(tasks),'profile':profile,'seed':seed,
         'tokenizer_server_model':config['model'],'chat_template_kwargs':config.get('chat_template_kwargs',{'enable_thinking':True}),
         'measurements':measurements,'notice':'Reuse this exact file for BOTH models. Lengths are tokenizer measurements, not character estimates.'})
