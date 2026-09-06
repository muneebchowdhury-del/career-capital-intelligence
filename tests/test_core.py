import json, tempfile, unittest
from pathlib import Path
from engine.core import safe_pattern_match,is_public_https_url,validate_dashboard,sha256_text
from engine.htmltools import meaningful_text,extract_links

ROOT=Path(__file__).resolve().parents[1]
class CoreTests(unittest.TestCase):
    def test_safe_wildcard(self):
        self.assertTrue(safe_pattern_match('semiconductor.*forecast','New SEMICONDUCTOR long term Forecast'))
        self.assertTrue(safe_pattern_match('World Energy Investment','World Energy Investment 2026'))
        self.assertFalse(safe_pattern_match('defense.*AI','defense spending'))
    def test_unsafe_pattern_rejected(self):
        with self.assertRaises(ValueError): safe_pattern_match('(a+)+$','aaaa')
    def test_url_policy(self):
        self.assertTrue(is_public_https_url('https://example.com/x',resolve_dns=False))
        self.assertFalse(is_public_https_url('http://example.com/x',resolve_dns=False))
        self.assertFalse(is_public_https_url('https://127.0.0.1/x',resolve_dns=False))
        self.assertFalse(is_public_https_url('https://localhost/x',resolve_dns=False))
    def test_meaningful_text_ignores_chrome(self):
        t=meaningful_text((ROOT/'tests/fixtures/page.html').read_text())
        self.assertIn('World Energy Investment 2026',t)
        self.assertNotIn('Global nav',t);self.assertNotIn('evil()',t);self.assertNotIn('Privacy',t)
    def test_link_extraction(self):
        x=extract_links((ROOT/'tests/fixtures/discovery.html').read_text(),'https://www.iea.org/topics/investment')
        self.assertEqual(x[0]['url'],'https://www.iea.org/reports/world-energy-investment-2026')
    def test_dashboard_valid(self):
        d=json.loads((ROOT/'data/recommendation_latest.json').read_text())
        self.assertEqual(validate_dashboard(d),[])
    def test_hash_deterministic(self):
        self.assertEqual(sha256_text('abc'),sha256_text('abc'))
