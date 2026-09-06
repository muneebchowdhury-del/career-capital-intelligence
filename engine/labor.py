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


def derive_labor_intelligence(rows: list[dict]) -> dict:
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
        if not latest:
            continue
        de=latest.get('Germany'); eu=latest.get('EU27')
        spread=None
        if de and eu:
            spread=round(float(de['value'])-float(eu['value']),3)
        sector={
            'dimension_key':dim,
            'dimension_label':label,
            'latest':{g:{'period':r.get('period'),'value':float(r['value']),'unit':r.get('unit','%')} for g,r in latest.items()},
            'momentum_4q_change':momentum,
            'persistence_5q_avg':persistence,
            'germany_vs_eu_spread':spread,
            'coverage_quarters':{g:len(v) for g,v in by_geo.items()},
        }
        sectors.append(sector)
    sectors.sort(key=lambda x:max((v['value'] for v in x['latest'].values()),default=-999),reverse=True)
    return {
        'methodology':{
            'vacancy_pressure':'Latest official job vacancy rate by NACE sector.',
            'momentum':'Change in vacancy rate from the oldest to newest observation within the latest five quarters.',
            'persistence':'Average job vacancy rate over up to the latest five quarters.',
            'germany_vs_eu_spread':'Germany latest vacancy rate minus EU27 latest vacancy rate for the same sector.',
            'ranking_use':'Evidence-only for now. These derived indicators do not automatically change opportunity scores.'
        },
        'sector_count':len(sectors),
        'sectors':sectors,
    }
