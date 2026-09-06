(async function(){
  const $=id=>document.getElementById(id);
  const statusEl=$('liveStatus'),syncChip=$('syncStatusChip'),evidenceChip=$('evidenceUpdatedChip'),lastRefreshChip=$('lastRefreshChip'),reviewQueueChip=$('reviewQueueChip'),snapshotCountChip=$('snapshotCountChip'),discoveryChip=$('discoveryChip'),nodeCountChip=$('nodeCountChip'),sourceCountChip=$('sourceCountChip'),versionChip=$('versionChip'),heroMetrics=$('heroMetrics'),historyFrom=$('historyFrom'),historyTo=$('historyTo'),historySummary=$('historySummary'),historyCompare=$('historyCompare'),liveSignals=$('liveSignals'),signalStatus=$('signalStatus'),signalCountChip=$('signalCountChip'),signalRunChip=$('signalRunChip');
  async function getJSON(url){if(window.__STATIC_FILES&&Object.prototype.hasOwnProperty.call(window.__STATIC_FILES,url))return structuredClone(window.__STATIC_FILES[url]);const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error(`${url}: ${r.status}`);return r.json()}
  function fmtDate(x){if(!x)return'—';const d=new Date(x);return Number.isNaN(d.valueOf())?String(x):d.toLocaleString()}
  function fmtObs(o){const v=Number(o?.value);if(!Number.isFinite(v))return'—';if(o.unit==='USD bn'){if(Math.abs(v)>=1000)return`$${(v/1000).toLocaleString(undefined,{maximumFractionDigits:3})}T`;return`$${v.toLocaleString(undefined,{maximumFractionDigits:1})}B`}return`${v.toLocaleString(undefined,{maximumFractionDigits:2})} ${o.unit||''}`.trim()}
  function renderHero(db){
    if(evidenceChip)evidenceChip.textContent=`Evidence: ${db.updated||'unknown'}`;
    if(nodeCountChip)nodeCountChip.textContent=`Opportunity nodes: ${(db.nodes||[]).length}`;
    if(sourceCountChip)sourceCountChip.textContent=`Evidence sources: ${(db.sources||[]).length}`;
    if(versionChip)versionChip.textContent=`Version: ${db.version||'—'}`;
    if(!heroMetrics)return;heroMetrics.textContent='';
    for(const a of db.heroAnchors||[]){const n=(db.nodes||[]).find(x=>x.id===a.nodeId),o=(n?.capitalObservations||[]).find(x=>x.series===a.series&&x.period===a.period);const row=document.createElement('div');row.className='metric';const span=document.createElement('span'),b=document.createElement('b');span.textContent=a.label;b.textContent=o?fmtObs(o):'—';row.append(span,b);heroMetrics.appendChild(row)}
    if(!(db.heroAnchors||[]).length)heroMetrics.textContent='No hero anchors configured.';
  }
  function option(select,h){const o=document.createElement('option');o.value=h.id;o.textContent=`${h.evidence_updated_at||'no evidence date'} · ${h.trigger||'snapshot'} · ${h.created_at}`;select.appendChild(o)}
  function scoreMap(n){return n?.scores||n||{}}
  function compareSnapshots(a,b){
    const am=new Map((a.nodes||[]).map(x=>[x.id,x])), bm=new Map((b.nodes||[]).map(x=>[x.id,x]));
    const added=[],removed=[],changed=[];
    for(const [id,n] of bm)if(!am.has(id))added.push(n.name||id);
    for(const [id,n] of am)if(!bm.has(id))removed.push(n.name||id);
    for(const [id,nb] of bm){const na=am.get(id);if(!na)continue;const sa=scoreMap(na),sb=scoreMap(nb),diffs={};for(const k of new Set([...Object.keys(sa),...Object.keys(sb)])){const x=Number(sa[k]),y=Number(sb[k]);if(Number.isFinite(x)&&Number.isFinite(y)&&x!==y)diffs[k]=Math.round((y-x)*100)/100}const capA=JSON.stringify(na.capitalObservations||[]),capB=JSON.stringify(nb.capitalObservations||[]);if(Object.keys(diffs).length||capA!==capB)changed.push({name:nb.name||id,scoreDiffs:diffs,capitalChanged:capA!==capB})}
    return{added,removed,changed};
  }
  function renderDiff(diff){historySummary.textContent='';const intro=document.createElement('div');intro.textContent=`${diff.changed.length} changed node(s), ${diff.added.length} added, ${diff.removed.length} removed.`;historySummary.appendChild(intro);for(const x of diff.changed.slice(0,6)){const d=document.createElement('div');d.style.marginTop='6px';const scores=Object.entries(x.scoreDiffs).slice(0,4).map(([k,v])=>`${k} ${v>0?'+':''}${v}`).join(', ');d.textContent=`${x.name}: ${scores||'capital observation changed'}${x.capitalChanged?' · capital evidence changed':''}`;historySummary.appendChild(d)}}
  function renderSignals(rows){
    if(!liveSignals)return;liveSignals.textContent='';
    if(!rows?.length){liveSignals.textContent='No structured signal observations yet. They appear after the first successful scheduled collector run.';return}
    for(const x of rows.slice(0,18)){const row=document.createElement('div');row.className='rawRow';const a=document.createElement('b'),b=document.createElement('span'),c=document.createElement('b'),d=document.createElement('span');a.textContent=x.metric_label||x.metric_key;b.textContent=`${x.geography||'—'} · ${x.dimension_label||x.dimension_key||'Total'}`;c.textContent=`${Number(x.value).toLocaleString(undefined,{maximumFractionDigits:2})} ${x.unit||''}`.trim();d.textContent=`${x.period} · fetched ${fmtDate(x.fetched_at)}`;row.append(a,b,c,d);liveSignals.appendChild(row)}
  }
  const db=await getJSON('./data/latest.json');renderHero(db);if(syncChip)syncChip.textContent='Data: static live snapshot';window.startCapitalDashboard(db);
  try{
    const st=await getJSON('./data/status.json');
    if(statusEl){statusEl.textContent='';const strong=document.createElement('b');strong.textContent=st.mode||'zero-cost static live';statusEl.append(strong,document.createTextNode(` · generated ${fmtDate(st.generated_at)} · latest evidence ${st.evidence_updated_at||db.updated||'—'}. Scheduled jobs update files; the frontend itself does not need rebuilding.`))}
    if(lastRefreshChip)lastRefreshChip.textContent=`Refresh: ${fmtDate(st.last_run?.completed_at)}`;
    if(reviewQueueChip)reviewQueueChip.textContent=`Review queue: ${st.pending_review??0}`;
    if(discoveryChip)discoveryChip.textContent=`New discoveries: ${st.new_discovered_items??0}`;
    if(snapshotCountChip)snapshotCountChip.textContent=`Snapshots: ${st.snapshot_count??0}`;
    if(sourceCountChip)sourceCountChip.textContent=`Evidence sources: ${(db.sources||[]).length}`;
    if(syncChip)syncChip.textContent='Data: Git-backed static live';
  }catch(e){if(statusEl)statusEl.textContent='Static data status unavailable: '+e.message}
  try{
    const rows=await getJSON('./data/signals-latest.json');renderSignals(rows);
    const st=await getJSON('./data/signal-status.json');if(signalStatus)signalStatus.textContent=`${st.observation_count||0} stored raw observation(s), ${st.current_observation_count||0} current. Latest collector: ${st.last_collector||'—'} · ${st.last_run_status||'—'}.`;if(signalCountChip)signalCountChip.textContent=`Signal observations: ${st.observation_count||0}`;if(signalRunChip)signalRunChip.textContent=`Signal refresh: ${fmtDate(st.last_run_at)}`;
  }catch(e){if(liveSignals)liveSignals.textContent='Structured signal files have not been generated yet.';if(signalStatus)signalStatus.textContent=e.message}
  let hist=[];
  try{hist=await getJSON('./data/history-index.json');historyFrom.textContent='';historyTo.textContent='';if(!hist.length){historySummary.textContent='No snapshots yet.';historyCompare.disabled=true}else{hist.forEach(x=>{option(historyFrom,x);option(historyTo,x)});historyTo.value=hist[0].id;historyFrom.value=(hist[1]||hist[0]).id;historyCompare.disabled=hist.length<2;historySummary.textContent=hist.length<2?'One snapshot exists. A later validated dataset will create comparison history.':'Choose two snapshots and compare validated changes.'}}catch(e){historySummary.textContent='History unavailable: '+e.message;historyCompare.disabled=true}
  if(historyCompare)historyCompare.onclick=async()=>{if(!historyFrom.value||!historyTo.value)return;historyCompare.disabled=true;historySummary.textContent='Comparing…';try{const [a,b]=await Promise.all([getJSON(`./data/history/${encodeURIComponent(historyFrom.value)}.json`),getJSON(`./data/history/${encodeURIComponent(historyTo.value)}.json`)]);renderDiff(compareSnapshots(a,b))}catch(e){historySummary.textContent='Could not compare snapshots: '+e.message}finally{historyCompare.disabled=false}};
})().catch(err=>{const el=document.getElementById('liveStatus');if(el)el.textContent='Could not load dashboard data: '+err.message;console.error(err)});
