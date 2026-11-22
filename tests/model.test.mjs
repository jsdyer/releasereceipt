import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import {shiftMonth, receipts, revision, csv} from '../web/model.mjs';
const source=JSON.parse(readFileSync(new URL('../web/receipts.json',import.meta.url))).releases;
test('calendar offsets cross January and use UTC',()=>assert.equal(shiftMonth('2026-03',-5),'2025-10'));
test('June 2026 links its first and two later source tables',()=>{
 const rows=receipts(source,'all').get('2026-06').filter(row=>row.published<='2026-10-30');
 assert.deepEqual(rows.map(r=>r.value),[0.3,0.4,0.4]); assert.equal(revision(rows),0.1);
 assert.equal(revision(rows.slice(1)),null); assert.equal(revision(rows.slice(0,1)),null);
 assert.match(csv(rows.map(r=>({...r,sector:'all'}))),/2026-06,all,2026-08-28,first table,0.3,https:/);
});
