"""Append observed StatCan vector vintages and publish RSS plus official release dates."""
import argparse,copy,hashlib,json,math,re,tempfile,urllib.request
from datetime import datetime,timezone,date
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from xml.etree.ElementTree import Element,SubElement,tostring
ROOT=Path(__file__).resolve().parents[1]
API='https://www150.statcan.gc.ca/t1/wds/rest/'
BASE='https://coolcode.ca/releasereceipt/'
def request(url,payload=None):
 req=urllib.request.Request(url,data=json.dumps(payload).encode() if payload is not None else None,headers={'User-Agent':'CoolCode ReleaseReceipt (+https://coolcode.ca/releasereceipt/)','Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=90) as r:
  if r.status!=200 or urlsplit(r.url).hostname!='www150.statcan.gc.ca':raise ValueError('Unexpected Statistics Canada response')
  raw=r.read(12_000_001)
 if len(raw)>12_000_000:raise ValueError('Response exceeds limit')
 return json.loads(raw)
def validate_config(c):
 ss=c['series']
 if not 1<=len(ss)<=c.get('max_series',100) or not 1<=c['latest_periods']<=240:raise ValueError('Invalid watchlist bounds')
 if len({s['vector'] for s in ss})!=len(ss):raise ValueError('Duplicate configured vector')
 for s in ss:
  if not isinstance(s['vector'],int) or s['vector']<=0 or not re.fullmatch(r'\d{8}',s['table']) or not s['label'].strip():raise ValueError('Invalid series')
def normalize(response,config):
 expected={s['vector']:s for s in config['series']};out={}
 for item in response:
  obj=item.get('object',{});v=obj.get('vectorId')
  if item.get('status')!='SUCCESS' or obj.get('responseStatusCode')!=0 or v not in expected or str(obj['productId'])!=expected[v]['table']:raise ValueError('Unexpected vector response')
  points=[]
  for p in obj.get('vectorDataPoint',[]):
   ref=p['refPer'];date.fromisoformat(ref[:10]);val=p.get('value')
   if val is not None and (not isinstance(val,(int,float)) or not math.isfinite(val)):raise ValueError('Invalid numeric value')
   # Suppression/unavailable symbols override any provider placeholder numeric value.
   if p.get('securityLevelCode',0)!=0 or p.get('statusCode',0) in [1,2,8,9,10]:val=None
   points.append({'period':ref,'value':val,'release_time':p['releaseTime'],'decimals':p['decimals'],'scalar':p['scalarFactorCode'],'symbol':p['symbolCode'],'status':p['statusCode'],'frequency':p['frequencyCode']})
  if not points or len({p['period'] for p in points})!=len(points):raise ValueError('Missing/duplicate vector periods')
  out[str(v)]=sorted(points,key=lambda p:p['period'])
 if set(out)!={str(v) for v in expected}:raise ValueError('Incomplete watchlist response')
 return out
def merge(previous,config,points,checked):
 data=copy.deepcopy(previous) if previous else {'schema':1,'started_at':checked,'series':{},'events':[]}
 if data.get('schema')!=1 or not isinstance(data.get('events'),list):raise ValueError('Invalid retained history')
 for s in config['series']:
  key=str(s['vector']);saved=data['series'].setdefault(key,{'definition':copy.deepcopy(s),'history':{}});saved['definition']=copy.deepcopy(s);saved['active']=True
  first=not saved['history'];events=[]
  for point in points[key]:
   history=saved['history'].setdefault(point['period'],[]);last=history[-1] if history else None;new={**point,'observed_at':checked}
   comparable=lambda p:{k:v for k,v in p.items() if k!='observed_at'}
   if last and comparable(last)==point:continue
   if last and point['release_time']<last['release_time']:raise ValueError('Source release time moved backwards')
   history.append(new)
   if not first:
    changed=last is not None and any(last.get(k)!=point.get(k) for k in ['value','scalar','symbol','status'])
    events.append({'vector':key,'label':s['label'],'period':point['period'],'type':'revision' if changed else 'release' if last else 'new period','old':last.get('value') if last else None,'value':point['value'],'release_time':point['release_time'],'observed_at':checked,'table':s['table']})
  if first:
   p=points[key][-1];events=[{'vector':key,'label':s['label'],'period':p['period'],'type':'initial capture','old':None,'value':p['value'],'release_time':p['release_time'],'observed_at':checked,'table':s['table']}]
  for event in events:
   event['id']=hashlib.sha256(json.dumps(event,sort_keys=True).encode()).hexdigest()[:24];data['events'].append(event)
 active={str(s['vector']) for s in config['series']}
 for key,s in data['series'].items():s['active']=key in active
 data['checked_at']=checked
 return data
def calendar(raw,config,checked):
 keys=sorted({s.get('calendar_match','') for s in config['series'] if s.get('calendar_match')}|{'Gross domestic product by industry'})
 today=checked[:10];events=[]
 for r in raw:
  if not any(r['title'].startswith(k) for k in keys):continue
  d=r['date'][:10];date.fromisoformat(d)
  if d<str(int(today[:4])-1)+'-01-01':continue
  url=r.get('url','')
  if url.startswith('/daily-quotidien/'):url='https://www150.statcan.gc.ca/n1'+url
  elif url.startswith('//'):url='https:'+url
  if url and (urlsplit(url).scheme!='https' or urlsplit(url).hostname not in ['www150.statcan.gc.ca','www.statcan.gc.ca']):raise ValueError('Unexpected calendar link')
  events.append({'date':d,'title':r['title'],'reference':r.get('description',''),'url':url,'scheduled':not bool(url)})
 if not events:raise ValueError('No matched official calendar events')
 return {'checked_at':checked,'source_url':config['calendar_url'],'events':events}
def rss(data,vector=None):
 root=Element('rss',version='2.0');channel=SubElement(root,'channel')
 for k,v in [('title','Release Receipt · '+('v'+vector if vector else 'StatCan watchlist')),('link',BASE),('description','Observed new periods and revisions. Initial capture is not the original release; source and observation dates are separate.')]:SubElement(channel,k).text=v
 for e in sorted([e for e in data['events'] if vector is None or e['vector']==vector],key=lambda e:(e['observed_at'],e['release_time']),reverse=True)[:200]:
  item=SubElement(channel,'item');SubElement(item,'title').text=f"{e['label']} · {e['type']} · {e['period'][:7]}"
  SubElement(item,'link').text=BASE+'?vector='+e['vector'];SubElement(item,'guid',isPermaLink='false').text=e['id']
  SubElement(item,'pubDate').text=format_datetime(datetime.fromisoformat(e['observed_at']).astimezone(timezone.utc),usegmt=True)
  SubElement(item,'description').text=f"Observed {e['observed_at']}. Source release {e['release_time']} (Eastern). Value {e['value']}; previous observed value {e['old']}. Source https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={e['table']}01"
 return b'<?xml version="1.0" encoding="utf-8"?>\n'+tostring(root,encoding='utf-8')
def main():
 p=argparse.ArgumentParser();p.add_argument('--calendar-file',type=Path);a=p.parse_args();config=json.loads((ROOT/'config/watchlist.json').read_text());validate_config(config)
 checked=datetime.now(timezone.utc).isoformat(timespec='seconds');response=request(API+'getDataFromVectorsAndLatestNPeriods',[{'vectorId':s['vector'],'latestN':config['latest_periods']} for s in config['series']]);points=normalize(response,config)
 file=ROOT/'web/watchlist.json';previous=json.loads(file.read_text()) if file.exists() else None
 data=merge(previous,config,points,checked);cal=calendar(json.loads(a.calendar_file.read_text()) if a.calendar_file else request(config['calendar_url']),config,checked)
 # Stage all outputs before mutation; a download/validation failure cannot replace good data.
 with tempfile.TemporaryDirectory(dir=ROOT/'web') as t:
  stage=Path(t);(stage/'watchlist.json').write_text(json.dumps(data,separators=(',',':'))+'\n');(stage/'calendar.json').write_text(json.dumps(cal,separators=(',',':'))+'\n');(stage/'feed.xml').write_bytes(rss(data));(stage/'feeds').mkdir()
  for key in data['series']:(stage/'feeds'/('v'+key+'.xml')).write_bytes(rss(data,key))
  (ROOT/'web/feeds').mkdir(exist_ok=True)
  for path in stage.rglob('*'):
   if path.is_file():path.replace(ROOT/'web'/path.relative_to(stage))
 print(f"{len(data['series'])} retained vectors, {len(data['events'])} dated change events, {len(cal['events'])} calendar events")
if __name__=='__main__':main()
