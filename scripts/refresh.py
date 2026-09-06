#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from engine.core import load_json,save_json,utcnow_iso,deterministic_id
from engine.store import FileStore
from engine.collectors import due,collect_signal,collect_watch,collect_discovery
DEFAULT_COLLECTORS={'signal':collect_signal,'report_watch':collect_watch,'discovery':collect_discovery}
def execute_refresh(sources,store,state,*,run_all=False,selected=None,now=None,collectors=None):
    collectors=collectors or DEFAULT_COLLECTORS; selected=set(selected or []); now=now or datetime.now(timezone.utc); started=utcnow_iso(); run_id=deterministic_id(started,'refresh',prefix='run_'); summary={'checked':0,'success':0,'failed':0,'new_observations':0,'changed_pages':0,'new_discoveries':0,'skipped':0}; errors=[]
    for src in sources:
        if selected and src['id'] not in selected: continue
        if not src.get('enabled',True): summary['skipped']+=1; continue
        if not run_all and not selected and not due(src,state,now): summary['skipped']+=1; continue
        summary['checked']+=1; st=state.setdefault(src['id'],{}); st['last_checked_at']=utcnow_iso()
        try:
            kind=src['kind']; fn=collectors.get(kind)
            if not fn: raise ValueError(f'unknown source kind: {kind}')
            if kind=='signal':
                rows,meta=fn(src,state); prepared=[]
                for row in rows: row=dict(row); row['fetched_at']=row.get('fetched_at') or utcnow_iso(); prepared.append(row)
                added=len(store.append_observations(prepared)); summary['new_observations']+=added; st.update({k:v for k,v in meta.items() if v is not None}); st['last_success_at']=utcnow_iso(); st['last_error']=None; st['last_result']={'rows':len(rows),'new':added}
            elif kind=='report_watch':
                result=fn(src,state)
                if result.get('changed'):
                    summary['changed_pages']+=1; cfg=src['config']; store.add_review(src['id'],'report_changed',src['name'],result.get('final_url') or cfg['sourceUrl'],{'old_fingerprint':st.get('fingerprint'),'new_fingerprint':result.get('fingerprint'),'text_chars':result.get('text_chars')})
                st.update({k:v for k,v in result.items() if k not in {'changed','not_modified'} and v is not None}); st['last_success_at']=utcnow_iso(); st['last_error']=None; st['last_result']={'changed':bool(result.get('changed')),'not_modified':bool(result.get('not_modified'))}
            elif kind=='discovery':
                items,meta=fn(src,state); baseline=not bool(st.get('last_success_at')); added_rows=store.append_discoveries([{'source_id':src['id'],'url':i['url'],'title':i['title'],'baseline':baseline} for i in items]); added=len(added_rows)
                if not baseline:
                    for rec in added_rows: store.add_review(src['id'],'new_report',rec.get('title') or rec['url'],rec['url'],{'discovery_id':rec['id']})
                summary['new_discoveries']+=0 if baseline else added; st.update({k:v for k,v in meta.items() if v is not None}); st['last_success_at']=utcnow_iso(); st['last_error']=None; st['last_result']={'found':len(items),'new':added,'baseline':baseline}
            summary['success']+=1
        except Exception as e:
            summary['failed']+=1; st['last_error']=f'{type(e).__name__}: {e}'[:1000]; errors.append({'source_id':src['id'],'error':st['last_error']})
        finally: store.save_state(state)
    completed=utcnow_iso(); status='success' if summary['failed']==0 else ('partial' if summary['success'] else 'failed'); row={'run_id':run_id,'started_at':started,'completed_at':completed,'status':status,'summary':summary,'errors':errors}; store.append_run(row); save_json(store.data/'status/last_run.json',row); return row
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--all',action='store_true'); ap.add_argument('--source',action='append',default=[]); ap.add_argument('--strict',action='store_true'); args=ap.parse_args(); registry=load_json(ROOT/'config/sources.json',{}) or {}; store=FileStore(ROOT); row=execute_refresh(registry.get('sources',[]),store,store.load_state(),run_all=args.all,selected=args.source); print(json.dumps(row,indent=2)); return 1 if args.strict and row['status']=='failed' else 0
if __name__=='__main__': raise SystemExit(main())
