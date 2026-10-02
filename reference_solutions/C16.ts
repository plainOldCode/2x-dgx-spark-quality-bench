export function solve(data: any): any {
  const stock: any={...data.stock}; const accepted: boolean[]=[];
  for (const order of data.orders) {
    const needed=new Map<string,number>();
    for (const x of order) needed.set(x.sku,(needed.get(x.sku)||0)+x.qty);
    const ok=[...needed].every(([k,n])=>(stock[k]??0)>=n); accepted.push(ok);
    if (ok) for (const [k,n] of needed) stock[k]-=n;
  }
  return {accepted,stock};
}
