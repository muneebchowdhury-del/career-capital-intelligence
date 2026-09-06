from __future__ import annotations
import json, sqlite3
from pathlib import Path
from .core import append_jsonl, canonical_json, deterministic_id, iter_jsonl, load_json, save_json, utcnow_iso

class FileStore:
    def __init__(self, root: Path):
        self.root=Path(root); self.data=self.root/'data'; self.state_path=self.data/'source_state.json'; self.reviews_path=self.data/'reviews.json'; self.run_path=self.data/'run_log.jsonl'
    def load_state(self): return load_json(self.state_path,{}) or {}
    def save_state(self,state): save_json(self.state_path,state)
    def reviews(self): return load_json(self.reviews_path,[]) or []
    def save_reviews(self,rows): save_json(self.reviews_path,rows)
    def add_review(self,source_id,kind,title,url,details=None):
        rows=self.reviews(); rid=deterministic_id(source_id,kind,url,title,prefix='rv_')
        if any(x.get('id')==rid for x in rows): return False,rid
        rows.append({'id':rid,'source_id':source_id,'kind':kind,'title':title,'url':url,'status':'pending','details':details or {},'created_at':utcnow_iso(),'resolved_at':None,'resolution_note':None}); self.save_reviews(rows); return True,rid
    def resolve_review(self,review_id,status,note=''):
        if status not in {'validated','published','rejected','duplicate','superseded'}: raise ValueError('invalid review status')
        rows=self.reviews(); found=False
        for x in rows:
            if x.get('id')==review_id: x['status']=status; x['resolved_at']=utcnow_iso(); x['resolution_note']=note; found=True; break
        if not found: raise KeyError(review_id)
        self.save_reviews(rows)
    def append_run(self,row): append_jsonl(self.run_path,row)
    def _obs_files(self): return sorted((self.data/'observations').glob('*.jsonl'))
    def all_observations(self):
        for p in self._obs_files(): yield from iter_jsonl(p)
    def current_observations(self):
        latest={}
        for r in self.all_observations():
            key=(r['source_id'],r['metric_key'],r.get('geography',''),r.get('dimension_key',''),r['period'])
            if key not in latest or int(r.get('revision',1))>=int(latest[key].get('revision',1)): latest[key]=r
        return list(latest.values())
    def append_observation(self,row:dict):
        return (lambda added: (bool(added), added[0]['id'] if added else next((x['id'] for x in self.current_observations() if (x['source_id'],x['metric_key'],x.get('geography',''),x.get('dimension_key',''),x['period'])==(row['source_id'],row['metric_key'],row.get('geography',''),row.get('dimension_key',''),row['period'])),None)))(self.append_observations([row]))
    def append_observations(self,rows):
        latest={}
        for r in self.current_observations(): latest[(r['source_id'],r['metric_key'],r.get('geography',''),r.get('dimension_key',''),r['period'])]=r
        added=[]
        for row in rows:
            row=dict(row)
            for k in ['source_id','metric_key','period','value','unit']:
                if k not in row: raise ValueError(f'missing observation {k}')
            logical=(row['source_id'],row['metric_key'],row.get('geography',''),row.get('dimension_key',''),row['period']); prev=latest.get(logical); value=float(row['value'])
            if prev and float(prev['value'])==value and prev.get('unit')==row.get('unit'): continue
            rev=(int(prev.get('revision',1))+1) if prev else 1
            rec=dict(row); rec['value']=value; rec['revision']=rev; rec['supersedes_id']=prev['id'] if prev else None; rec['fetched_at']=rec.get('fetched_at') or utcnow_iso(); rec['id']=deterministic_id(*logical,rev,prefix='obs_'); latest[logical]=rec; added.append(rec)
        grouped={}
        for rec in added: grouped.setdefault(self.data/'observations'/f"{rec['fetched_at'][:7]}.jsonl",[]).append(rec)
        for path,recs in grouped.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('a',encoding='utf-8',newline='\n') as f:
                for rec in recs: f.write(canonical_json(rec)+'\n')
        return added
    def append_discoveries(self,rows):
        existing=set()
        for p in sorted((self.data/'discoveries').glob('*.jsonl')):
            for x in iter_jsonl(p): existing.add(x.get('id'))
        added=[]
        for row in rows:
            rec=dict(row); rec.setdefault('found_at',utcnow_iso()); rec.setdefault('id',deterministic_id(rec.get('source_id'),rec.get('url'),prefix='disc_'))
            if rec['id'] in existing: continue
            existing.add(rec['id']); added.append(rec)
        grouped={}
        for rec in added: grouped.setdefault(self.data/'discoveries'/f"{rec['found_at'][:7]}.jsonl",[]).append(rec)
        for path,recs in grouped.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('a',encoding='utf-8',newline='\n') as f:
                for rec in recs: f.write(canonical_json(rec)+'\n')
        return added
    def append_discovery(self,row:dict):
        probe=dict(row); probe.setdefault('found_at',utcnow_iso()); probe.setdefault('id',deterministic_id(probe.get('source_id'),probe.get('url'),prefix='disc_')); added=self.append_discoveries([probe]); return (True,probe['id']) if added else (False,probe['id'])

def build_sqlite(root:Path,output:Path):
    root=Path(root); store=FileStore(root); output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists(): output.unlink()
    con=sqlite3.connect(output)
    con.executescript('''PRAGMA journal_mode=DELETE;
CREATE TABLE signal_observations(id TEXT PRIMARY KEY,source_id TEXT NOT NULL,metric_key TEXT NOT NULL,metric_label TEXT,geography TEXT,dimension_key TEXT,dimension_label TEXT,period TEXT NOT NULL,value REAL NOT NULL,unit TEXT NOT NULL,revision INTEGER NOT NULL,supersedes_id TEXT,fetched_at TEXT NOT NULL,source_url TEXT);
CREATE INDEX idx_obs_logical ON signal_observations(source_id,metric_key,geography,dimension_key,period,revision);
CREATE TABLE discoveries(id TEXT PRIMARY KEY,source_id TEXT,url TEXT NOT NULL,title TEXT,baseline INTEGER,found_at TEXT);
CREATE TABLE reviews(id TEXT PRIMARY KEY,source_id TEXT,kind TEXT,title TEXT,url TEXT,status TEXT,created_at TEXT,resolved_at TEXT,resolution_note TEXT,details_json TEXT);
CREATE TABLE source_state(source_id TEXT PRIMARY KEY,payload_json TEXT NOT NULL);
CREATE TABLE source_registry(source_id TEXT PRIMARY KEY,kind TEXT,name TEXT,enabled INTEGER,cadence_days REAL,config_json TEXT);
CREATE TABLE runs(run_id TEXT PRIMARY KEY,started_at TEXT,completed_at TEXT,status TEXT,summary_json TEXT,errors_json TEXT);
CREATE TABLE snapshots(snapshot_id TEXT PRIMARY KEY,content_hash TEXT,created_at TEXT,evidence_updated_at TEXT,version TEXT,trigger TEXT,payload_json TEXT NOT NULL);''')
    for r in store.all_observations(): con.execute('INSERT INTO signal_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(r['id'],r['source_id'],r['metric_key'],r.get('metric_label'),r.get('geography'),r.get('dimension_key'),r.get('dimension_label'),r['period'],float(r['value']),r['unit'],int(r.get('revision',1)),r.get('supersedes_id'),r.get('fetched_at'),r.get('source_url')))
    for p in sorted((store.data/'discoveries').glob('*.jsonl')):
        for x in iter_jsonl(p): con.execute('INSERT OR IGNORE INTO discoveries VALUES (?,?,?,?,?,?)',(x.get('id'),x.get('source_id'),x.get('url'),x.get('title'),1 if x.get('baseline') else 0,x.get('found_at')))
    for x in store.reviews(): con.execute('INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?,?,?)',(x['id'],x.get('source_id'),x.get('kind'),x.get('title'),x.get('url'),x.get('status'),x.get('created_at'),x.get('resolved_at'),x.get('resolution_note'),json.dumps(x.get('details',{}),ensure_ascii=False)))
    for sid,payload in store.load_state().items(): con.execute('INSERT INTO source_state VALUES (?,?)',(sid,json.dumps(payload,ensure_ascii=False,sort_keys=True)))
    registry=load_json(root/'config/sources.json',{}) or {}
    for x in registry.get('sources',[]): con.execute('INSERT INTO source_registry VALUES (?,?,?,?,?,?)',(x.get('id'),x.get('kind'),x.get('name'),1 if x.get('enabled',True) else 0,float(x.get('cadenceDays',7)),json.dumps(x.get('config',{}),ensure_ascii=False,sort_keys=True)))
    if store.run_path.exists():
        for x in iter_jsonl(store.run_path): con.execute('INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?)',(x.get('run_id'),x.get('started_at'),x.get('completed_at'),x.get('status'),json.dumps(x.get('summary',{}),ensure_ascii=False,sort_keys=True),json.dumps(x.get('errors',[]),ensure_ascii=False,sort_keys=True)))
    snap_idx=load_json(root/'data/snapshots/index.json',[]) or []
    for meta in snap_idx:
        sp=root/'data/snapshots'/f"{meta['id']}.json"
        if sp.exists(): con.execute('INSERT INTO snapshots VALUES (?,?,?,?,?,?,?)',(meta.get('id'),meta.get('content_hash'),meta.get('created_at'),meta.get('evidence_updated_at'),meta.get('version'),meta.get('trigger'),json.dumps(load_json(sp,{}),ensure_ascii=False,sort_keys=True)))
    con.commit(); con.close(); return output
