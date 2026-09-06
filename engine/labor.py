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


def derive_labor_intelligence(rows: list[dict], node_map: dict | None=None) -> dict:
    groups=defaultdict(list)
    for r in rows:
        if r.get('metric_key')!='job_vacancy_rate':
            continue
        key=(r.get('dimension_key',''),r.get('dimension_label',''))
        groups[key].append(r)
    sectors=[]
    for (dim,label),items in groups.items():
        items=sorted(items,key=lambda x:(_period_key(x.get('period')),x.get('geography','')))
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
            if recent:
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
    by_key={s['dimension_key']:s for s in sectors}
    node_signals=[]
    for node_id,cfg in (node_map or {}).items():
        keys=cfg.get('nace_keys',[]) if isinstance(cfg,dict) else []
        weight=float(cfg.get('weight',1.0)) if isinstance(cfg,dict) else 1.0
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
        if evidence:
            node_signals.append({'node_id':node_id,'mapping_weight':weight,'evidence':evidence,'status':'evidence_only'})
    return {
        'methodology':{
            'vacancy_pressure':'Latest official job vacancy rate by NACE sector.',
            'momentum':'Change in vacancy rate from the oldest to newest observation within the latest five quarters.',
            'persistence':'Average job vacancy rate over up to the latest five quarters.',
            'germany_vs_eu_spread':'Germany latest vacancy rate minus EU27 latest vacancy rate for the same sector.',
            'node_mapping':'Opportunity nodes are linked to broad NACE sectors only where the relationship is defensible. Mapping is intentionally many-to-one and evidence-only.',
            'ranking_use':'Evidence-only for now. These derived indicators do not automatically change opportunity scores.'
        },
        'sector_count':len(sectors),
        'mapped_node_count':len(node_signals),
        'sectors':sectors,
        'node_signals':node_signals,
    }
