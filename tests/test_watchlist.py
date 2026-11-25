import copy,json,sys,unittest
from pathlib import Path
from xml.etree import ElementTree
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from watchlist import merge,normalize,calendar,rss,validate_config
S={'vector':1,'table':'18100004','label':'A & B','unit':'Index','calendar_match':'Consumer Price Index'}
C={'series':[S],'latest_periods':36,'calendar_url':'https://www150.statcan.gc.ca/calendar'}
P={'period':'2026-01-01','value':100,'release_time':'2026-02-01T08:30','decimals':1,'scalar':0,'symbol':0,'status':0,'frequency':6}
class WatchlistTests(unittest.TestCase):
 def test_append_only_revision_and_removed_config_history(self):
  a=merge(None,C,{'1':[P]},'2026-02-02T00:00:00+00:00');b=merge(a,C,{'1':[{**P,'value':110,'release_time':'2026-03-01T08:30'}]},'2026-03-02T00:00:00+00:00');self.assertEqual(len(a['series']['1']['history'][P['period']]),1);self.assertEqual(len(b['series']['1']['history'][P['period']]),2);self.assertEqual(b['events'][-1]['type'],'revision');d=merge(b,{'series':[]},{},'2026-04-02T00:00:00+00:00');self.assertFalse(d['series']['1']['active']);self.assertEqual(d['events'],b['events'])
 def test_repeat_does_not_create_revision(self):
  a=merge(None,C,{'1':[P]},'2026-02-02T00:00:00+00:00');b=merge(a,C,{'1':[P]},'2026-02-03T00:00:00+00:00');self.assertEqual(len(b['events']),1);self.assertEqual(a['started_at'],b['started_at'])
 def test_regression_and_bad_previous_fail(self):
  a=merge(None,C,{'1':[P]},'2026-02-02T00:00:00+00:00')
  with self.assertRaises(ValueError):merge(a,C,{'1':[{**P,'release_time':'2025-01-01T08:30'}]},'2026-02-03T00:00:00+00:00')
  with self.assertRaises(ValueError):merge({'schema':2},C,{'1':[P]},'2026-02-03T00:00:00+00:00')
 def test_add_new_vector_is_not_limited_to_starters(self):
  c={**C,'series':[S,{**S,'vector':2}]};validate_config(c);d=merge(None,c,{'1':[P],'2':[P]},'2026-02-02T00:00:00+00:00');self.assertEqual(len(d['series']),2)
 def test_rss_xml_and_guid_are_stable(self):
  a=merge(None,C,{'1':[P]},'2026-02-02T00:00:00+00:00');tree=ElementTree.fromstring(rss(a));self.assertIn('A & B',tree.findtext('channel/item/title'));self.assertEqual(tree.findtext('channel/item/guid'),a['events'][0]['id'])
 def test_actual_calendar_not_cadence_guess_and_link_validation(self):
  rows=[{'date':'2026-12-14 00:00:01','title':'Consumer Price Index','description':'November','url':''}];d=calendar(rows,C,'2026-11-25');self.assertEqual(d['events'][0]['date'],'2026-12-14');self.assertTrue(d['events'][0]['scheduled']);rows[0]['url']='https://evil.test/'
  with self.assertRaises(ValueError):calendar(rows,C,'2026-11-25')
 def test_status_and_symbol_codes_not_confused(self):
  p={'refPer':'2026-01-01','value':100,'releaseTime':'2026-02-01T08:30','decimals':1,'scalarFactorCode':0,'symbolCode':3,'statusCode':4,'securityLevelCode':0,'frequencyCode':6}
  response=[{'status':'SUCCESS','object':{'responseStatusCode':0,'vectorId':1,'productId':18100004,'vectorDataPoint':[p]}}];self.assertEqual(normalize(response,C)['1'][0]['value'],100);p['statusCode']=8;self.assertIsNone(normalize(response,C)['1'][0]['value'])
if __name__=='__main__':unittest.main()
