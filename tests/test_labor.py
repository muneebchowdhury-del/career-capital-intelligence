import unittest
from engine.labor import derive_labor_intelligence

class LaborIntelligenceTests(unittest.TestCase):
    def test_derives_pressure_momentum_persistence_and_spread(self):
        rows=[]
        de=[2.0,2.2,2.4,2.3,2.8]; eu=[1.8,1.9,2.0,2.1,2.4]
        periods=['2025-Q2','2025-Q3','2025-Q4','2026-Q1','2026-Q2']
        for geo,vals in [('Germany',de),('EU27',eu)]:
            for p,v in zip(periods,vals):
                rows.append({'source_id':'x','metric_key':'job_vacancy_rate','metric_label':'Job vacancy rate','geography':geo,'dimension_key':'K','dimension_label':'Information services','period':p,'value':v,'unit':'%'})
        out=derive_labor_intelligence(rows,{'cloud-dist':{'nace_keys':['K'],'weight':0.75}})
        self.assertEqual(out['sector_count'],1)
        s=out['sectors'][0]
        self.assertEqual(s['latest']['Germany']['value'],2.8)
        self.assertEqual(s['momentum_4q_change']['Germany'],0.8)
        self.assertAlmostEqual(s['persistence_5q_avg']['Germany'],2.34)
        self.assertAlmostEqual(s['germany_vs_eu_spread'],0.4)
        self.assertEqual(out['mapped_node_count'],1)
        self.assertEqual(out['node_signals'][0]['node_id'],'cloud-dist')
        self.assertEqual(out['node_signals'][0]['status'],'evidence_only')

    def test_keeps_nace_revisions_metric_specific(self):
        rows=[
            {'metric_key':'job_vacancy_rate','geography':'Germany','dimension_key':'K','dimension_label':'ICT services new NACE','period':'2026-Q1','value':2.7,'unit':'%'},
            {'metric_key':'labor_cost_yoy','geography':'Germany','dimension_key':'J','dimension_label':'Information and communication old NACE','period':'2026-Q1','value':5.9,'unit':'%'},
            {'metric_key':'labor_cost_yoy','geography':'Germany','dimension_key':'K','dimension_label':'Financial and insurance old NACE','period':'2026-Q1','value':1.9,'unit':'%'}
        ]
        out=derive_labor_intelligence(rows,{'ai-infra':{'vacancy_nace_keys':['K'],'labor_cost_nace_keys':['J'],'weight':0.7}})
        node=out['node_signals'][0]
        self.assertEqual(node['vacancy_evidence'][0]['dimension_label'],'ICT services new NACE')
        self.assertEqual(node['labor_cost_evidence'][0]['dimension_label'],'Information and communication old NACE')
        self.assertNotEqual(node['labor_cost_evidence'][0]['dimension_key'],'K')
        self.assertEqual(out['labor_cost_sector_count'],2)

    def test_ignores_unrecognized_metrics(self):
        out=derive_labor_intelligence([{'metric_key':'other','dimension_key':'K','period':'2026-Q1','value':1,'unit':'%'}],{})
        self.assertEqual(out['sector_count'],0)
        self.assertEqual(out['labor_cost_sector_count'],0)
        self.assertEqual(out['mapped_node_count'],0)

if __name__=='__main__': unittest.main()
