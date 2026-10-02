from __future__ import annotations
import json, os, time, urllib.request, urllib.error
import ipaddress
from urllib.parse import urlsplit
from .common import digest

class APIError(RuntimeError): pass

def _is_loopback(host: str) -> bool:
    normalized=host.split('%',1)[0].rstrip('.').lower()
    if normalized == 'localhost': return True
    try: return ipaddress.ip_address(normalized).is_loopback
    except ValueError: return False

class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    # Do not forward Authorization headers to a redirect target.
    def redirect_request(self,req,fp,code,msg,headers,newurl): return None

class Client:
    def __init__(self,config: dict):
        self.config=config
        base=config['base_url'].rstrip('/')
        try:
            parsed=urlsplit(base)
            _port=parsed.port
        except ValueError as e: raise ValueError('Invalid endpoint URL') from e
        if parsed.scheme not in ('http','https') or not parsed.hostname:
            raise ValueError('Endpoint URL must use http or https and include a hostname')
        if parsed.username is not None or parsed.password is not None:
            raise ValueError('Do not put credentials in the endpoint URL; use the configured environment variable')
        if parsed.query or parsed.fragment:
            raise ValueError('Endpoint URL must not contain a query or fragment')
        if parsed.scheme == 'http' and not _is_loopback(parsed.hostname):
            raise ValueError('Plain HTTP is allowed only for loopback endpoints; use HTTPS for network endpoints')
        self.api=base if base.endswith('/v1') else base+'/v1'
        self.root=self.api[:-3]
        self.model=config['model']
        keyvar=config.get('api_key_env','VLLM_API_KEY')
        self.key=os.environ.get(keyvar,'')
        self.timeout=float(config.get('timeout_s',900))
        self.opener=urllib.request.build_opener(_NoRedirectHandler)
    def request(self,url,body=None):
        headers={'Content-Type':'application/json'}
        if self.key: headers['Authorization']='Bearer '+self.key
        req=urllib.request.Request(url,data=None if body is None else json.dumps(body,ensure_ascii=False,allow_nan=False).encode(),headers=headers)
        start=time.perf_counter()
        try:
            with self.opener.open(req,timeout=self.timeout) as r:
                data=r.read(16*1024*1024+1)
                if len(data)>16*1024*1024: raise APIError('Response exceeds 16 MiB limit')
                result=json.loads(data)
        except urllib.error.HTTPError as e:
            detail=e.read(4096).decode('utf-8','replace')
            raise APIError(f'HTTP {e.code}: {detail}') from e
        except (urllib.error.URLError,TimeoutError,ValueError) as e:
            raise APIError(str(e)) from e
        return result,time.perf_counter()-start
    def check_model(self):
        data,_=self.request(self.api+'/models')
        names=[x.get('id') for x in data.get('data',[])]
        if self.model not in names: raise APIError(f'Served model {self.model!r} not found. Available ids: {names}')
        return data
    def chat(self,body): return self.request(self.api+'/chat/completions',body)
    def tokenize(self,messages,tools=None):
        payload={'model':self.model,'messages':messages,'add_generation_prompt':True,
                 'chat_template_kwargs':self.config.get('chat_template_kwargs',{'enable_thinking':True})}
        if tools: payload['tools']=tools
        data,_=self.request(self.root+'/tokenize',payload)
        count=data.get('count')
        if not isinstance(count,int) and isinstance(data.get('tokens'),list): count=len(data['tokens'])
        if not isinstance(count,int): raise APIError('/tokenize did not return count or token IDs; no character-based fallback is allowed')
        return {'count':count,'token_ids_sha256':digest(data['tokens']) if isinstance(data.get('tokens'),list) else None}
