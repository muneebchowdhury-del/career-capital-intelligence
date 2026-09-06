from __future__ import annotations
from collections import defaultdict
from statistics import mean


def _period_key(p: str):
    s=str(p or '')
    if '-Q' in s:
        try:
            y,q=s.split('-Q',1); return (int(y),int(q))
        except Exception: pass
    try: return (int(s[:4]),0)
    except Exception: return (0,0)


def _derive_metric(rows: list[dict], metric_key: str) -> list[dict]:
    groups=defaultdict(list)
    for r in rows:
        if r.get('metric_key')!=metric_key: continue
        groups[(r.get('dimension_key',''),r.get('dimension_label',''))].append(r)
    sectors=[]
    for (dim,label),items in groups.items():
        by_geo=defaultdict(list)
        for r in items: by_geo[r.get('geography','')].append(r)
        latest={}; momentum={}; persistence={}
        for geo,vals in by_geo.items():
            vals=sorted(vals,key=lambda x:_period_key(x.get('period')))
            if not vals: continue
            latest[geo]=vals[-1]
            recent=vals[-5:]
            if len(recent)>=2:
                momentum[geo]=round(float(recent[-1]['value'])-float(recent[0]['value']),3)
            persistence[geo]=round(mean(float(x['value']) for x in recent),3)
        if not latest: continue
        de=latest.get('Germany'); eu=latest.get('EU27')
        spread=round(float(de['value'])-float(eu['value']),3) if de and eu else None
        sectors.append({
            'dimension_key':dim,
            'dimension_label':label,
            'latest':{g:{'period':r.get('period'),'value':float(r['value']),'unit':r.get('unit','%')} for g,r in latest.items()},
            'momentum_4q_change':momentum,
            'persistence_5q_avg':persistence,
            'germany_vs_eu_spread':spread,
            'coverage_quarters':{g:len(v) for g,v in by_geo.items()},
        })
    sectors.sort(key=lambda x:max((v['value'] for v in x['latest'].values()),default=-999),reverse=True)
    return sectors


def _sector_signal(sector: dict, geography: str):
    latest=(sector.get('latest') or {}).get(geography)
    if not latest: return None
    return {
        'dimension_key':sector.get('dimension_key'),
        'dimension_label':sector.get('dimension_label'),
        'latest_rate':latest.get('value'),
        'latest_period':latest.get('period'),
        'momentum_4q_change':(sector.get('momentum_4q_change') or {}).get(geography),
        'persistence_5q_avg':(sector.get('persistence_5q_avg') or {}).get(geography),
        'coverage_quarters':(sector.get('coverage_quarters') or {}).get(geography,0),
    }


def _mapped_evidence(keys, by_key):
    evidence=[]
    for key in keys:
        sec=by_key.get(key)
        if not sec: continue
        evidence.append({
            'dimension_key':key,
            'dimension_label':sec.get('dimension_label'),
            'Germany':_sector_signal(sec,'Germany'),
            'EU27':_sector_signal(sec,'EU27'),
            'germany_vs_eu_spread':sec.get('germany_vs_eu_spread'),
        })
    return evidence


def derive_labor_intelligence(rows: list[dict], node_map: dict | None=None) -> dict:
    vacancy=_derive_metric(rows,'job_vacancy_rate')
    labor_cost=_derive_metric(rows,'labor_cost_yoy')
    vacancy_by_key={s['dimension_key']:s for s in vacancy}
    cost_by_key={s['dimension_key']:s for s in labor_cost}
    node_signals=[]
    for node_id,cfg in (node_map or {}).items():
        if not isinstance(cfg,dict): continue
        vacancy_keys=cfg.get('vacancy_nace_keys',cfg.get('nace_keys',[]))
        cost_keys=cfg.get('labor_cost_nace_keys',[])
        vacancy_evidence=_mapped_evidence(vacancy_keys,vacancy_by_key)
        labor_cost_evidence=_mapped_evidence(cost_keys,cost_by_key)
        if not vacancy_evidence and not labor_cost_evidence: continue
        node_signals.append({
            'node_id':node_id,
            'mapping_weight':float(cfg.get('weight',1.0)),
            'vacancy_evidence':vacancy_evidence,
            'labor_cost_evidence':labor_cost_evidence,
            'evidence':vacancy_evidence,
            'status':'evidence_only'
        })
    return {
        'methodology':{
            'vacancy_pressure':'Latest official job vacancy rate by NACE sector.',
            'vacancy_momentum':'Change in vacancy rate from the oldest to newest observation within the latest five quarters.',
            'vacancy_persistence':'Average job vacancy rate over up to the latest five quarters.',
            'labor_cost_pressure':'Latest year-over-year change in nominal hourly labour costs by NACE sector.',
            'labor_cost_momentum':'Change in the year-over-year labour-cost growth rate from the oldest to newest observation within the latest five quarters; this is cost acceleration/deceleration, not hiring growth.',
            'germany_vs_eu_spread':'Germany latest value minus EU27 latest value for the same metric and sector.',
            'coding_guardrail':'Vacancy and labour-cost feeds use different NACE revisions. Their sector-code mappings are stored separately and are never joined by code alone.',
            'node_mapping':'Opportunity nodes are linked to broad NACE sectors only where the relationship is defensible. Mapping is intentionally many-to-one and evidence-only.',
            'ranking_use':'Evidence-only for now. These derived indicators do not automatically change opportunity scores.'
        },
        'sector_count':len(vacancy),
        'labor_cost_sector_count':len(labor_cost),
        'mapped_node_count':len(node_signals),
        'sectors':vacancy,
        'labor_cost_sectors':labor_cost,
        'metrics':{
            'job_vacancy_rate':{'sector_count':len(vacancy),'sectors':vacancy},
            'labor_cost_yoy':{'sector_count':len(labor_cost),'sectors':labor_cost}
        },
        'node_signals':node_signals,
    }
