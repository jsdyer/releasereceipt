import {receipts, revision, sectors, csv} from './model.mjs';
const get = id => document.getElementById(id);
const monthName = month => new Intl.DateTimeFormat('en-CA', {month:'long',year:'numeric',timeZone:'UTC'}).format(new Date(month+'-01T00:00:00Z'));
const signed = n => (n > 0 ? '+' : '') + n.toFixed(1);
const rate = n => signed(n)+'%';
function option(value, content) {
  return new Option(content, value);
}
async function init() {
  const response = await fetch('./receipts.json');
  if (!response.ok) throw new Error('archive unavailable');
  const archive = await response.json();
  let grouped;
  function draw() {
    const key = get('month').value;
    const rows = grouped.get(key);
    const first = rows.find(row=>row.initial);
    const latest = rows.at(-1);
    const diff = revision(rows);
    get('selection').textContent = monthName(key)+' · '+sectors[get('sector').value];
    get('first-date').textContent = first?.published || '';
    get('latest-date').textContent = latest.published;
    get('first').textContent = first ? rate(first.value) : 'Outside archive';
    get('latest').textContent = rate(latest.value);
    get('difference').textContent = diff === null ? '—' : signed(diff)+' pp';
    get('interpretation').textContent = diff === null ? (first ? 'Only the first table is available so far.' : 'The earliest archived entry already includes a revision.') : diff === 0 ? 'The latest figure matches the first published rate at the precision shown.' : 'The growth estimate moved '+(diff>0 ? 'up ' : 'down ')+Math.abs(diff).toFixed(1)+' percentage points between these releases.';
    get('ledger').replaceChildren(...rows.map(row=>{
      const tr=document.createElement('tr');
      for (const value of [row.published, rate(row.value), row.initial ? 'Preliminary' : 'Later release']) tr.insertCell().textContent=value;
      const a=document.createElement('a'); a.href=row.table; a.textContent='Open table ↗'; tr.insertCell().append(a); return tr;
    }));
    const url=new URL(location.href); url.searchParams.set('month',key); url.searchParams.set('sector',get('sector').value); history.replaceState(null,'',url);
  }
  function group(initialMonth) {
    grouped = receipts(archive.releases, get('sector').value);
    const months=[...grouped.keys()].sort().reverse();
    get('month').replaceChildren(...months.map(m=>option(m,monthName(m))));
    const ranking=months.map(month=>({month, diff:revision(grouped.get(month))})).filter(m=>m.diff!==null).sort((a,b)=>Math.abs(b.diff)-Math.abs(a.diff));
    get('month').value = grouped.has(initialMonth) ? initialMonth : (ranking[0]?.month ?? months[0]);
    get('ranking').replaceChildren(...ranking.slice(0,5).map(({month,diff})=>{
      const li=document.createElement('li'), b=document.createElement('button'); b.textContent=monthName(month)+' · '+signed(diff)+' pp';
      b.addEventListener('click',()=>{get('month').value=month;draw();get('selection').scrollIntoView({block:'center'});}); li.append(b); return li;
    }));
    draw();
  }
  const params=new URL(location.href).searchParams;
  if (Object.hasOwn(sectors,params.get('sector'))) get('sector').value=params.get('sector');
  group(params.get('month'));
  get('month').addEventListener('change',draw);
  get('sector').addEventListener('change',()=>group(get('month').value));
  get('download').addEventListener('click',()=>{
    const sector=get('sector').value, month=get('month').value;
    const text=csv(grouped.get(month).map(row=>({...row,sector})));
    const url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));
    const a=document.createElement('a'); a.href=url; a.download='gdp-'+month+'-'+sector+'.csv'; a.click(); setTimeout(()=>URL.revokeObjectURL(url),30000);
  });
  const dates=archive.releases.map(r=>r.published).sort();
  get('status').textContent=dates.length+' Statistics Canada releases · '+dates[0]+' through '+dates.at(-1)+' · Source checked '+archive.checked;
  get('explorer').hidden=false;
}
init().catch(()=>{get('status').textContent='The release archive could not be loaded. Reload or report an issue below.';});
