import json, sqlite3, tempfile, unittest
from pathlib import Path
from engine.store import FileStore,build_sqlite
from engine.core import save_json

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'data/observations').mkdir(parents=True);(self.root/'data/discoveries').mkdir(parents=True);(self.root/'data/status').mkdir(parents=True)
        self.s=FileStore(self.root)
    def tearDown(self): self.tmp.cleanup()
    def row(self,v): return {'source_id':'S','metric_key':'vacancy','metric_label':'Vacancy','geography':'DE','dimension_key':'J','dimension_label':'Info','period':'2026-Q1','value':v,'unit':'%','source_url':'https://example.com'}
    def test_observation_dedupe_and_revision(self):
        a,id1=self.s.append_observation(self.row(3.1));self.assertTrue(a)
        a,id2=self.s.append_observation(self.row(3.1));self.assertFalse(a);self.assertEqual(id1,id2)
        a,id3=self.s.append_observation(self.row(3.0));self.assertTrue(a);self.assertNotEqual(id1,id3)
        cur=self.s.current_observations();self.assertEqual(len(cur),1);self.assertEqual(cur[0]['revision'],2);self.assertEqual(cur[0]['supersedes_id'],id1)
        self.assertEqual(len(list(self.s.all_observations())),2)
    def test_batch_observations_dedupe_and_revision(self):
        rows=[self.row(3.1),dict(self.row(3.1),dimension_key='K',dimension_label='Finance')]
        self.assertEqual(len(self.s.append_observations(rows)),2)
        self.assertEqual(len(self.s.append_observations(rows)),0)
        changed=[self.row(3.0),dict(self.row(3.1),dimension_key='K',dimension_label='Finance')]
        self.assertEqual(len(self.s.append_observations(changed)),1)
        cur={x['dimension_key']:x for x in self.s.current_observations()}
        self.assertEqual(cur['J']['revision'],2);self.assertEqual(cur['K']['revision'],1)
    def test_batch_discoveries(self):
        rows=[{'source_id':'D','url':'https://example.com/a','title':'A'},{'source_id':'D','url':'https://example.com/b','title':'B'}]
        self.assertEqual(len(self.s.append_discoveries(rows)),2);self.assertEqual(len(self.s.append_discoveries(rows)),0)

    def test_review_lifecycle(self):
        added,rid=self.s.add_review('S','new_report','Title','https://example.com/r');self.assertTrue(added)
        added2,rid2=self.s.add_review('S','new_report','Title','https://example.com/r');self.assertFalse(added2);self.assertEqual(rid,rid2)
        self.s.resolve_review(rid,'validated','checked')
        r=self.s.reviews()[0];self.assertEqual(r['status'],'validated');self.assertEqual(r['resolution_note'],'checked')
    def test_discovery_dedupe(self):
        ok,did=self.s.append_discovery({'source_id':'D','url':'https://example.com/r','title':'R'});self.assertTrue(ok)
        ok2,did2=self.s.append_discovery({'source_id':'D','url':'https://example.com/r','title':'R'});self.assertFalse(ok2);self.assertEqual(did,did2)
    def test_sqlite_rebuild(self):
        self.s.append_observation(self.row(3.1));self.s.append_observation(self.row(3.0));self.s.add_review('S','new_report','T','https://example.com/r')
        out=build_sqlite(self.root,self.root/'build/db.sqlite')
        con=sqlite3.connect(out);self.assertEqual(con.execute('select count(*) from signal_observations').fetchone()[0],2);self.assertEqual(con.execute('select count(*) from reviews').fetchone()[0],1);con.close()
