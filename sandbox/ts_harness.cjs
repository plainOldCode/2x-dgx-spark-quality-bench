'use strict';
const fs = require('node:fs');
const {isDeepStrictEqual} = require('node:util');
const mod = require(process.argv[2]);
const inputs = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
for (const data of inputs) {
  const before = structuredClone(data);
  try {
    const value = mod.solve(data);
    if (value && typeof value.then === 'function') throw new Error('solve must be synchronous');
    if (value === undefined) throw new Error('solve returned undefined');
    process.stdout.write(JSON.stringify({ok:true,value,mutated:!isDeepStrictEqual(data,before)})+'\n');
  } catch (e) {
    process.stdout.write(JSON.stringify({ok:false,error:String(e).slice(0,500)})+'\n');
  }
}
