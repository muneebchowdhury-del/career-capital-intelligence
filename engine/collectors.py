from __future__ import annotations
import gzip,json,time
from datetime import datetime,timezone,timedelta
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode,urljoin,urlparse
from urllib.request import Request,build_opener,HTTPRedirectHandler,HTTPSHandler
from .core import MAX_BODY_BYTES,is_public_https_url,safe_pattern_match,sha256_text
from .htmltools import meaningful_text,extract_links
USER_AGENT='CapitalCareerIntel/5.0 (+public research dashboard; respectful scheduled fetch)'
class SafeRedirect(HTTPRedirectHandler):
    max_redirections=5
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        target=urljoin(req.full_url,newurl)
        if not is_public_https_url(target): raise URLError(f'unsafe redirect target: {target}')
        return super().redirect_request(req,fp,code,msg,headers,target)
def safe_fetch(url:str,*,headers=None,timeout=20,retries=1,max_bytes=MAX_BODY_BYTES):
    if not is_public_https_url(url): raise ValueError(f'unsafe URL: {url}')
    opener=build_opener(SafeRedirect(),HTTPSHandler()); hdr={'User-Agent':USER_AGENT,'Accept':'application/json,text/html;q=0.9,*/*;q=0.5','Accept-Encoding':'gzip'}; hdr.update(headers or {}); last=None
    for attempt in range(retries+1):
        try:
            with opener.open(Request(url,headers=hdr,method='GET'),timeout=timeout) as r:
                final=r.geturl()
                if not is_public_https_url(final): raise URLError('unsafe final URL')
                data=r.read(max_bytes+1)
                if len(data)>max_bytes: raise ValueError('response too large')
                if (r.headers.get('Content-Encoding') or '').lower()=='gzip':
                    data=gzip.decompress(data)
                    if len(data)>max_bytes: raise ValueError('decompressed response too large')
                return data,dict(r.headers.items()),final
        except Exception as e:
            last=e
            if attempt<retries: time.sleep(min(2**attempt,4))
    raise last
def due(source:dict,state:dict,now=None):
    if not source.get('enabled',True): return False
    st=state.get(source['id']) or {}; last=st.get('last_checked_at')
    if not last: return True
    try: dt=datetime.fromisoformat(last.replace('Z','+00:00'))
    except Exception: return True
    now=now or datetime.now(timezone.utc); cadence=float(source.get('cadenceDays',7)); wait=min(cadence,1.0) if st.get('last_error') else cadence; return now-dt>=timedelta(days=wait)
def category_positions(cat):
    idx=cat.get('index',{})
    if isinstance(idx,list): return {name:i for i,name in enumerate(idx)}
    if isinstance(idx,dict): return {str(k):int(v) for k,v in idx.items()}
    return {}
def parse_eurostat_jsonstat(payload,cfg):
    ids=payload.get('id') or []; sizes=payload.get('size') or []; values=payload.get('value') or []; dims=payload.get('dimension') or {}
    if len(ids)!=len(sizes): raise ValueError('JSON-stat id/size mismatch')
    series_dim=cfg['seriesDimension']; time_dim=cfg['timeDimension']
    if series_dim not in ids or time_dim not in ids: raise ValueError('required dimension missing')
    maps={d:category_positions(dims[d]['category']) for d in ids}; labels={d:(dims[d]['category'].get('label') or {}) for d in ids}; inv={d:{pos:key for key,pos in maps[d].items()} for d in ids}; total=1
    for s in sizes: total*=int(s)
    def value_at(i):
        if isinstance(values,list): return values[i] if i<len(values) else None
        if isinstance(values,dict): return values.get(str(i),values.get(i))
    strides=[]; acc=1
    for s in reversed(sizes[1:]): acc*=int(s); strides.insert(0,acc)
    strides.append(1); rows=[]
    for flat in range(total):
        rem=flat; coords=[]
        for stride,size in zip(strides,sizes): pos=rem//stride; rem%=stride; coords.append(pos)
        v=value_at(flat)
        if v is None: continue
        bydim={d:inv[d].get(int(pos),str(pos)) for d,pos in zip(ids,coords)}; skey=bydim[series_dim]; tkey=bydim[time_dim]
        rows.append({'source_id':cfg['sourceId'],'metric_key':cfg['metricKey'],'metric_label':cfg.get('metricLabel',cfg['metricKey']),'geography':cfg.get('geography',''),'dimension_key':skey,'dimension_label':labels[series_dim].get(skey,skey),'period':tkey,'value':float(v),'unit':cfg.get('unit',''),'source_url':cfg.get('sourceUrl')})
    rows.sort(key=lambda r:(r['period'],r['dimension_key']),reverse=True); allowed=[]
    for r in rows:
        if r['dimension_key'] not in allowed:
            if len(allowed)>=int(cfg.get('maxSeries',40)): continue
            allowed.append(r['dimension_key'])
    return [r for r in rows if r['dimension_key'] in allowed]
def collect_signal(source,state):
    cfg=source['config']; raw_query=cfg.get('incrementalQuery') if state.get(source['id'],{}).get('last_success_at') else cfg.get('bootstrapQuery'); query=dict(raw_query or {})
    # Eurostat's current employment-indicator code for Job Vacancy Rate is JVR.
    # Older seed configurations used JOBRATE; translate it at runtime so historical
    # config files remain reproducible while the collector follows the current code list.
    if cfg.get('adapter')=='eurostat_jsonstat_dimension_history' and str(query.get('indic_em','')).upper()=='JOBRATE':
        query['indic_em']='JVR'
    url=cfg['endpoint']+('?' + urlencode(query)); body,headers,final=safe_fetch(url,headers={'Accept':'application/json'}); payload=json.loads(body.decode('utf-8'))
    if cfg.get('adapter')=='eurostat_jsonstat_dimension_history':
        rows=parse_eurostat_jsonstat(payload,cfg)
        if not rows:
            values=payload.get('value')
            value_count=len(values) if isinstance(values,(list,dict)) else None
            raise ValueError(f"Eurostat returned zero rows; ids={payload.get('id')!r}; size={payload.get('size')!r}; value_count={value_count!r}; label={payload.get('label')!r}")
        return rows,{'final_url':final,'etag':headers.get('ETag'),'last_modified':headers.get('Last-Modified')}
    raise ValueError(f"unknown signal adapter {cfg.get('adapter')}")
def collect_watch(source,state):
    cfg=source['config']; prev=state.get(source['id'],{}); hdr={}
    if prev.get('etag'): hdr['If-None-Match']=prev['etag']
    if prev.get('last_modified'): hdr['If-Modified-Since']=prev['last_modified']
    try: body,headers,final=safe_fetch(cfg['sourceUrl'],headers=hdr)
    except HTTPError as e:
        if e.code==304: return {'changed':False,'not_modified':True,'fingerprint':prev.get('fingerprint'),'text_chars':prev.get('text_chars',0),'final_url':cfg['sourceUrl'],'etag':prev.get('etag'),'last_modified':prev.get('last_modified')}
        raise
    text=meaningful_text(body.decode('utf-8','replace'))
    if len(text)<int(cfg.get('minTextChars',200)): raise ValueError(f'page text too short ({len(text)})')
    low=text.casefold()
    if any(x in low for x in ['verify you are human','captcha','access denied','cloudflare ray id']): raise ValueError('bot-block/interstitial detected')
    fp=sha256_text(text); return {'changed':bool(prev.get('fingerprint') and prev.get('fingerprint')!=fp),'not_modified':False,'fingerprint':fp,'text_chars':len(text),'final_url':final,'etag':headers.get('ETag'),'last_modified':headers.get('Last-Modified')}
def collect_discovery(source,state):
    cfg=source['config']; body,headers,final=safe_fetch(cfg['discoveryUrl']); html=body.decode('utf-8','replace'); text=meaningful_text(html)
    if len(text)<int(cfg.get('minTextChars',200)): raise ValueError('discovery page too short')
    base_host=urlparse(final).hostname; out=[]
    for x in extract_links(html,final):
        if cfg.get('sameHost') and urlparse(x['url']).hostname!=base_host: continue
        blob=(x['text']+' '+x['url']).strip(); inc=cfg.get('includeAny') or []; exc=cfg.get('excludeAny') or []
        if inc and not any(safe_pattern_match(p,blob) for p in inc): continue
        if exc and any(safe_pattern_match(p,blob) for p in exc): continue
        if not is_public_https_url(x['url']): continue
        out.append({'url':x['url'],'title':x['text'] or x['url']})
        if len(out)>=int(cfg.get('maxItems',100)): break
    return out,{'final_url':final,'etag':headers.get('ETag'),'last_modified':headers.get('Last-Modified')}
