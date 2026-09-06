import json,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from engine.collectors import parse_eurostat_jsonstat,due
from engine.core import safe_pattern_match
from engine.htmltools import extract_links
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
class CollectorTests(unittest.TestCase):
    def cfg(self): return {'sourceId':'EURO','metricKey':'job_vacancy_rate','metricLabel':'Job vacancy rate','unit':'%','geography':'Germany','seriesDimension':'nace_r2_1','timeDimension':'time','maxSeries':40,'sourceUrl':'https://example.com'}
    def test_eurostat_parser(self):
        p=json.loads((ROOT/'tests/fixtures/eurostat.json').read_text());rows=parse_eurostat_jsonstat(p,self.cfg());self.assertEqual(len(rows),6)
        q=[x for x in rows if x['dimension_key']=='J' and x['period']=='2026-Q1'][0];self.assertEqual(q['value'],1.3);self.assertEqual(q['dimension_label'],'Information')
    def test_due_logic(self):
        src={'id':'s','enabled':True,'cadenceDays':7};now=datetime(2026,9,5,tzinfo=timezone.utc)
        self.assertTrue(due(src,{},now));self.assertFalse(due(src,{'s':{'last_checked_at':(now-timedelta(days=2)).isoformat()}},now));self.assertTrue(due(src,{'s':{'last_checked_at':(now-timedelta(days=8)).isoformat()}},now));self.assertFalse(due(src,{'s':{'last_checked_at':(now-timedelta(hours=12)).isoformat(),'last_error':'down'}},now));self.assertTrue(due(src,{'s':{'last_checked_at':(now-timedelta(days=1,minutes=1)).isoformat(),'last_error':'down'}},now))
    def test_discovery_filter_semantics(self):
        links=extract_links((ROOT/'tests/fixtures/discovery.html').read_text(),'https://www.iea.org/topics/investment');host='www.iea.org';out=[]
        for x in links:
            if urlparse(x['url']).hostname!=host:continue
            blob=x['text']+' '+x['url']
            if not safe_pattern_match('World Energy Investment',blob):continue
            if safe_pattern_match('podcast',blob):continue
            out.append(x)
        self.assertEqual(len(out),1)
