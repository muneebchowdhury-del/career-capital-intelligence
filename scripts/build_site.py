#!/usr/bin/env python3
from __future__ import annotations
import json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from engine.core import canonical_json,load_json,save_json,sha256_text,utcnow_iso,validate_dashboard,iter_jsonl,load_source_registry
from engine.store import FileStore,build_sqlite
from engine.labor import derive_labor_intelligence
def last_runs(store,n=20):
    if not store.run_path.exists(): return []
    return list(iter_jsonl(store.run_path))[-n:][::-1]
def current_snapshots(): return load_json(ROOT/'data/snapshots/index.json',[]) or []
def ensure_snapshot(db):
    idx=current_snapshots(); h=sha256_text(canonical_json(db))
    if idx and idx[0].get('content_hash')==h: return idx
    sid='snap_'+h[:16]; ts=utcnow_iso(); path=ROOT/'data/snapshots'/f'{sid}.json'
    if not path.exists(): save_json(path,db)
    meta={'id':sid,'content_hash':h,'created_at':ts,'evidence_updated_at':db.get('updated'),'version':db.get('version'),'trigger':'validated_dataset'}; idx=[meta]+[x for x in idx if x.get('id')!=sid]; save_json(ROOT/'data/snapshots/index.json',idx); return idx
def main():
    store=FileStore(ROOT); docs=ROOT/'docs'; ddata=docs/'data'; ddata.mkdir(parents=True,exist_ok=True); db=load_json(ROOT/'data/recommendation_latest.json'); errs=validate_dashboard(db)
    if errs: raise SystemExit('Dashboard validation failed:\n- '+'\n- '.join(errs))
    idx=ensure_snapshot(db); save_json(ddata/'latest.json',db); hdir=ddata/'history'; hdir.mkdir(parents=True,exist_ok=True)
    for meta in idx[:100]:
        src=ROOT/'data/snapshots'/f"{meta['id']}.json"
        if src.exists(): shutil.copy2(src,hdir/f"{meta['id']}.json")
    save_json(ddata/'history-index.json',idx[:100]); current=store.current_observations(); current.sort(key=lambda x:(x.get('fetched_at',''),x.get('period','')),reverse=True); save_json(ddata/'signals-latest.json',current[:500])
    labor_map=load_json(ROOT/'config/labor-node-map.json',{}) or {}; labor=derive_labor_intelligence(current,labor_map); labor['generated_at']=utcnow_iso(); save_json(ddata/'labor-intelligence.json',labor)
    runs=last_runs(store,20); reviews=store.reviews(); sources=load_source_registry(ROOT); overrides=load_json(ROOT/'config/automation_overrides.json',{}) or {}; manual_ids=set(overrides.get('manual_review_only',[])); state=store.load_state(); enabled=[s for s in sources if s.get('enabled',True)]; automated=[s for s in enabled if s.get('id') not in manual_ids]; manual=[s for s in enabled if s.get('id') in manual_ids]; last=runs[0] if runs else None
    failed_automated=[{'source_id':sid,'error':x.get('last_error')} for sid,x in state.items() if x.get('last_error') and sid not in manual_ids]
    manual_sources=[{'source_id':s.get('id'),'name':s.get('name'),'last_error':(state.get(s.get('id')) or {}).get('last_error')} for s in manual]
    status={'mode':'zero-cost static live','generated_at':utcnow_iso(),'evidence_updated_at':db.get('updated'),'version':db.get('version'),'source_count':len(enabled),'automated_source_count':len(automated),'manual_review_source_count':len(manual),'snapshot_count':len(idx),'pending_review':sum(1 for r in reviews if r.get('status')=='pending'),'new_discovered_items':sum(1 for r in reviews if r.get('status')=='pending' and r.get('kind')=='new_report'),'last_run':last,'failed_sources':failed_automated,'manual_review_sources':manual_sources}; save_json(ddata/'status.json',status)
    signal_status={'observation_count':len(list(store.all_observations())),'current_observation_count':len(current),'last_run_at':last.get('completed_at') if last else None,'last_run_status':last.get('status') if last else None,'last_collector':current[0].get('source_id') if current else None,'labor_sector_count':labor.get('sector_count',0),'labor_cost_sector_count':labor.get('labor_cost_sector_count',0),'ict_occupation_mix_count':labor.get('occupation_mix_count',0),'labor_mapped_node_count':labor.get('mapped_node_count',0)}; save_json(ddata/'signal-status.json',signal_status); save_json(ddata/'reviews.json',[r for r in reviews if r.get('status')=='pending']); build_sqlite(ROOT,ROOT/'build/intelligence.sqlite'); save_json(ROOT/'build/database_manifest.json',{'generated_at':utcnow_iso(),'sqlite':'build/intelligence.sqlite','canonical_store':'data/*.json + data/**/*.jsonl','observations':signal_status['observation_count'],'reviews':len(reviews),'snapshots':len(idx)}); print(json.dumps(status,indent=2))
if __name__=='__main__': main()
