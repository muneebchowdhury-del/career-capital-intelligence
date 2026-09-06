import json, re, sqlite3, subprocess, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ProjectTests(unittest.TestCase):
    def test_static_bootstrap_no_runtime_api(self):
        s=(ROOT/'docs/bootstrap.js').read_text()
        self.assertNotIn('/api/dashboard',s);self.assertNotIn('/api/status',s);self.assertIn('./data/latest.json',s)
    def test_frontend_contract_ids(self):
        html=(ROOT/'docs/index.html').read_text();boot=(ROOT/'docs/bootstrap.js').read_text();core=(ROOT/'docs/app-core.js').read_text()
        ids=set(re.findall(r'id="([A-Za-z0-9_-]+)"',html))
        refs=set(re.findall(r"\$\('([A-Za-z0-9_-]+)'\)",boot+core))
        missing=refs-ids
        self.assertEqual(missing,set(),f'missing DOM ids: {missing}')
    def test_generated_json_exists_and_valid(self):
        for rel in ['docs/data/latest.json','docs/data/status.json','docs/data/signals-latest.json','docs/data/signal-status.json','docs/data/history-index.json']:
            p=ROOT/rel;self.assertTrue(p.exists(),rel);json.loads(p.read_text())
    def test_latest_has_nodes(self):
        d=json.loads((ROOT/'docs/data/latest.json').read_text());self.assertGreaterEqual(len(d['nodes']),16);self.assertGreaterEqual(len(d['sources']),20)
    def test_source_registry(self):
        d=json.loads((ROOT/'config/sources.json').read_text());ids=[x['id'] for x in d['sources']];self.assertEqual(len(ids),len(set(ids)));self.assertTrue(any(x['kind']=='signal' for x in d['sources']));self.assertTrue(any(x['kind']=='discovery' for x in d['sources']))
    def test_workflows_zero_cost(self):
        text='\n'.join(p.read_text() for p in (ROOT/'.github/workflows').glob('*.yml'))
        self.assertIn('actions/checkout@v6',text);self.assertIn('actions/setup-python@v7',text);self.assertNotIn('wrangler',text.lower());self.assertNotIn('aws',text.lower())
    def test_no_secrets_in_repo_config(self):
        bad=re.compile(r'(api[_-]?key|secret|password)\s*[:=]\s*["\']?[A-Za-z0-9_-]{12,}',re.I)
        for base in ['config','scripts','engine','docs']:
            for p in (ROOT/base).rglob('*'):
                if p.is_file() and p.suffix in {'.py','.js','.json','.html','.md'}:
                    self.assertIsNone(bad.search(p.read_text(errors='ignore')),str(p))
    def test_standalone_embeds_data(self):
        p=ROOT/'STANDALONE_PREVIEW.html';self.assertTrue(p.exists());s=p.read_text();self.assertIn('window.__STATIC_FILES=',s);self.assertNotIn('<script src="./app-core.js"',s)
