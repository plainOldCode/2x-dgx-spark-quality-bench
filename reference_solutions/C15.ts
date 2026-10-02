export function solve(data: any): any {
  let s: any={status:'idle',requestId:null,items:[],error:null};
  for (const e of data.events) {
    if (e.type==='start') s={...s,status:'loading',requestId:e.requestId,error:null};
    else if (s.status==='loading' && s.requestId===e.requestId) {
      if (e.type==='success') s={status:'success',requestId:null,items:[...e.items],error:null};
      else if (e.type==='failure') s={...s,status:'error',requestId:null,error:e.error};
      else if (e.type==='cancel') s={...s,status:'idle',requestId:null,error:null};
    }
  }
  return s;
}
