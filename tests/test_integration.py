import json, shutil, sqlite3, subprocess, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class IntegrationTests(unittest.TestCase):
    def test_build_site_repeatable(self):
        subprocess.run([sys.executable if False else 'python','scripts/build_site.py'],cwd=ROOT,check=True,capture_output=True,text=True)
        a=json.loads((ROOT/'docs/data/latest.json').read_text());h1=json.loads((ROOT/'docs/data/history-index.json').read_text())
        subprocess.run(['python','scripts/build_site.py'],cwd=ROOT,check=True,capture_output=True,text=True)
        b=json.loads((ROOT/'docs/data/latest.json').read_text());h2=json.loads((ROOT/'docs/data/history-index.json').read_text())
        self.assertEqual(a,b);self.assertEqual(len(h1),len(h2))
    def test_local_sqlite_is_queryable(self):
        subprocess.run(['python','scripts/build_site.py'],cwd=ROOT,check=True,capture_output=True,text=True)
        con=sqlite3.connect(ROOT/'build/intelligence.sqlite');tables={x[0] for x in con.execute("select name from sqlite_master where type='table'")};con.close();self.assertTrue({'signal_observations','discoveries','reviews','source_state','source_registry','runs','snapshots'}<=tables)
