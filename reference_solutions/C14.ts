export function solve(data: any): any {
  const m = /^([+-]?)([0-9]+)(?:\.([0-9]{1,2}))?$/.exec(data.amount.trim());
  if (!m) return {error:'invalid_amount'};
  let n = BigInt(m[2])*100n + BigInt((m[3] || '').padEnd(2,'0'));
  if (m[1] === '-') n = -n;
  return {cents:n.toString()};
}
