from __future__ import annotations
import re, string
from .common import equivalent, strict_loads

def final_text(message: dict) -> tuple[str,str | None]:
    """Never select an answer from reasoning_content. Preserve raw messages separately."""
    content=message.get('content')
    if content is None: return '',None
    if not isinstance(content,str): return '', 'non_text_content'
    s=content.strip()
    if s.startswith('<think>'):
        end=s.find('</think>')
        if end<0: return '', 'unclosed_think_block'
        return s[end+len('</think>'):].strip(), 'removed_explicit_think_prefix'
    return s,None

def checks(text: str,spec: dict) -> dict[str,bool]:
    lines=text.splitlines(); body=[x[2:] if x.startswith('- ') else x for x in lines]
    words=[x.strip(string.punctuation) for x in text.split()]
    ans={}
    if 'bullet_lines' in spec: ans['bullet_lines']=len(lines)==spec['bullet_lines'] and all(x.startswith('- ') for x in lines)
    if 'line_count' in spec: ans['line_count']=len(lines)==spec['line_count']
    if 'words_per_line' in spec: ans['words_per_line']=bool(body) and all(len(x.split())==spec['words_per_line'] for x in body)
    if 'second_contains' in spec: ans['second_contains']=len(body)>=2 and spec['second_contains'] in [x.strip(string.punctuation) for x in body[1].split()]
    if 'banned' in spec: ans['banned']=not any(re.search(r'\b'+re.escape(w)+r'\b',text,re.I) for w in spec['banned'])
    if 'one_period_per_line' in spec: ans['one_period_per_line']=bool(body) and all(x.endswith('.') and x.count('.')==1 for x in body)
    if 'word_count' in spec: ans['word_count']=len(text.split())==spec['word_count']
    if 'single_paragraph' in spec: ans['single_paragraph']='\n' not in text and '\r' not in text and not text.startswith(('- ','* ','#'))
    for w,n in spec.get('token_occurrences',{}).items(): ans['occurrences_'+w]=words.count(w)==n
    if 'initials' in spec: ans['initials']=''.join(x[:1] for x in lines)==spec['initials']
    if 'line_required' in spec:
        ans['line_required']=len(lines)==len(spec['line_required']) and all(all(w in x for w in ws) for x,ws in zip(lines,spec['line_required']))
    if 'allowed_numbers' in spec: ans['allowed_numbers']=all(x in spec['allowed_numbers'] for x in re.findall(r'\d+',text))
    if spec.get('no_ascii_letters'): ans['no_ascii_letters']=not re.search(r'[A-Za-z]',text)
    return ans

def grade_text(text: str,oracle: dict) -> dict:
    kind=oracle['kind']
    if kind in ('json','tool'):
        try: actual=strict_loads(text)
        except (ValueError,TypeError): return {'passed':False,'score':0.0,'reason':'invalid_json','checks':{'valid_json':False}}
        passed=equivalent(actual,oracle['expected'])
        return {'passed':passed,'score':float(passed),'reason':'ok' if passed else 'answer_mismatch','checks':{'valid_json':True,'exact_answer':passed}}
    if kind=='text':
        passed=text.strip()==oracle['expected'].strip()
        return {'passed':passed,'score':float(passed),'reason':'ok' if passed else 'text_mismatch'}
    if kind=='constraints':
        result=checks(text,oracle['checks']); passed=bool(text) and all(result.values())
        return {'passed':passed,'score':sum(result.values())/len(result) if result else 0.0,'reason':'ok' if passed else 'constraint_failure','checks':result}
    raise ValueError('Cannot text-grade '+kind)

class ToolSimulator:
    """Each stage is an unordered set; stages themselves are ordered.
    No real function, shell, filesystem, network or service is called.
    """
    def __init__(self,oracle: dict):
        import copy
        self.stages=copy.deepcopy(oracle['stages']); self.stage=0; self.error=None; self.trace=[]
    @property
    def complete(self): return self.stage==len(self.stages) and not self.error
    def process(self,calls: list[dict]) -> list[dict]:
        results=[]; ids=set()
        # A dependent later stage cannot be guessed in the same response as its prerequisite.
        batch_stage=self.stage
        for raw in calls:
            try:
                cid=raw['id']; fn=raw['function']; name=fn['name']; args=strict_loads(fn['arguments'])
                if not isinstance(cid,str) or not cid or cid in ids: raise ValueError('invalid or duplicate call id')
                ids.add(cid)
                if self.stage>=len(self.stages) or self.stage!=batch_stage: raise ValueError('unexpected or premature call')
                match=next((i for i,x in enumerate(self.stages[self.stage]) if x['name']==name and equivalent(x['arguments'],args)),None)
                if match is None: raise ValueError('wrong tool, arguments, duplicate call, or ordering')
                record=self.stages[self.stage].pop(match)
                self.trace.append({'name':name,'arguments':args,'valid':True})
                results.append({'role':'tool','tool_call_id':cid,'content':__import__('json').dumps(record['result'],ensure_ascii=False)})
                if not self.stages[self.stage]: self.stage+=1
            except (KeyError,TypeError,ValueError) as e:
                self.error=str(e); self.trace.append({'raw':raw,'valid':False,'error':str(e)}); break
        return results
