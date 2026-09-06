import importlib.util,tempfile,unittest
from pathlib import Path
from engine.store import FileStore

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('refreshmod',ROOT/'scripts/refresh.py');refresh=importlib.util.module_from_spec(spec);spec.loader.exec_module(refresh)

class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);(self.root/'data/observations').mkdir(parents=True);(self.root/'data/discoveries').mkdir(parents=True);(self.root/'data/status').mkdir(parents=True);self.store=FileStore(self.root)
    def tearDown(self):self.t.cleanup()
    def test_failure_isolation_and_partial_status(self):
        sources=[{'id':'good','kind':'signal','name':'Good','enabled':True,'cadenceDays':1,'config':{}},{'id':'bad','kind':'signal','name':'Bad','enabled':True,'cadenceDays':1,'config':{}}]
        def fake(src,state):
            if src['id']=='bad':raise RuntimeError('upstream down')
            return ([{'source_id':'GOOD','metric_key':'m','metric_label':'M','geography':'DE','dimension_key':'J','dimension_label':'Info','period':'2026-Q1','value':1.0,'unit':'%','source_url':'https://example.com'}],{})
        row=refresh.execute_refresh(sources,self.store,{},run_all=True,collectors={'signal':fake})
        self.assertEqual(row['status'],'partial');self.assertEqual(row['summary']['success'],1);self.assertEqual(row['summary']['failed'],1);self.assertEqual(len(self.store.current_observations()),1)
    def test_manual_sources_are_skipped_by_automation_but_explicitly_targetable(self):
        sources=[{'id':'auto','kind':'signal','name':'Auto','enabled':True,'cadenceDays':1,'config':{}},{'id':'manual','kind':'signal','name':'Manual','enabled':True,'cadenceDays':1,'config':{}}]
        calls=[]
        def fake(src,state):
            calls.append(src['id'])
            return ([{'source_id':src['id'],'metric_key':'m','metric_label':'M','geography':'DE','dimension_key':'J','dimension_label':'Info','period':'2026-Q1','value':1.0,'unit':'%','source_url':'https://example.com'}],{})
        row=refresh.execute_refresh(sources,self.store,{},run_all=True,collectors={'signal':fake},manual_ids={'manual'})
        self.assertEqual(calls,['auto']);self.assertEqual(row['summary']['manual_skipped'],1);self.assertEqual(row['summary']['failed'],0)
        calls.clear();row2=refresh.execute_refresh(sources,self.store,{},selected=['manual'],collectors={'signal':fake},manual_ids={'manual'})
        self.assertEqual(calls,['manual']);self.assertEqual(row2['summary']['success'],1)
    def test_discovery_baseline_then_review(self):
        src={'id':'d','kind':'discovery','name':'D','enabled':True,'cadenceDays':1,'config':{}}
        calls=[[{'url':'https://example.com/one','title':'One'}],[{'url':'https://example.com/one','title':'One'},{'url':'https://example.com/two','title':'Two'}]]
        def fake(s,state):return calls.pop(0),{}
        state={}
        r1=refresh.execute_refresh([src],self.store,state,run_all=True,collectors={'discovery':fake});self.assertEqual(r1['summary']['new_discoveries'],0);self.assertEqual(self.store.reviews(),[])
        r2=refresh.execute_refresh([src],self.store,state,run_all=True,collectors={'discovery':fake});self.assertEqual(r2['summary']['new_discoveries'],1);self.assertEqual(len(self.store.reviews()),1)
    def test_page_change_creates_review_only_after_baseline(self):
        src={'id':'w','kind':'report_watch','name':'Watch','enabled':True,'cadenceDays':1,'config':{'sourceUrl':'https://example.com/r'}}
        seq=[{'changed':False,'fingerprint':'a','text_chars':500,'final_url':'https://example.com/r'},{'changed':True,'fingerprint':'b','text_chars':520,'final_url':'https://example.com/r'}]
        def fake(s,state):return seq.pop(0)
        state={};refresh.execute_refresh([src],self.store,state,run_all=True,collectors={'report_watch':fake});self.assertEqual(len(self.store.reviews()),0)
        refresh.execute_refresh([src],self.store,state,run_all=True,collectors={'report_watch':fake});self.assertEqual(len(self.store.reviews()),1)
