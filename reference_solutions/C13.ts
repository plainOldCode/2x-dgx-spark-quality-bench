export function solve(data: any): any {
  const m = new Map<string, any>();
  for (const r of data.records) { const old = m.get(r.id); if (!old || r.version >= old.version) m.set(r.id, {...r}); }
  return [...m.values()].sort((a,b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
}
