(async function(){
  const $=id=>document.getElementById(id);
  function installProfileControlsUX(){
    const style=document.createElement('style');
    style.textContent=`
      .profileRow{grid-template-columns:44px 1fr minmax(100px,1.4fr) 42px 90px}
      .profileRow.inactive{opacity:1}
      .profileRow.inactive>label,.profileRow.inactive>input[type=range],.profileRow.inactive>output,.profileRow.inactive>select{opacity:.46}
      .profileRow>label{cursor:pointer;user-select:none}
      .profileRow input[type=checkbox]{appearance:none;-webkit-appearance:none;width:38px;height:22px;margin:0;border:1px solid #3b5368;border-radius:999px;background:#253544;position:relative;cursor:pointer;opacity:1;transition:.15s}
      .profileRow input[type=checkbox]::after{content:"";position:absolute;width:16px;height:16px;left:2px;top:2px;border-radius:50%;background:#d9e6f1;transition:.15s}
      .profileRow input[type=checkbox]:checked{background:#1688a6;border-color:#46d9ff;box-shadow:0 0 0 2px rgba(70,217,255,.12)}
      .profileRow input[type=checkbox]:checked::after{transform:translateX(16px);background:#fff}
      .profileRow input[type=checkbox]:focus-visible{outline:2px solid #46d9ff;outline-offset:2px}
      .profileRow input[type=range]:disabled,.profileRow select:disabled{cursor:not-allowed}
      @media(max-width:700px){.profileRow{grid-template-columns:44px 1fr 1fr 38px}.profileRow select{grid-column:2/5}}
    `;
    document.head.appendChild(style);
    const root=$('profile');
    if(!root)return;
    root.addEventListener('click',e=>{
      const label=e.target.closest('.profileRow>label');
      if(!label)return;
      const box=label.parentElement?.querySelector('input[type=checkbox]');
      if(box)box.click();
    });
  }
  installProfileControlsUX();
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
  function strategicSectors(rows){return (rows||[]).filter(x=>/^[A-Z]$/.test(x.dimension_key||'')).sort((a,b)=>Number(b.latest?.Germany?.value??-999)-Number(a.latest?.Germany?.value??-999))}
  function addLaborRows(target,rows,metric){
    target.textContent='';
    const list=strategicSectors(rows).slice(0,8);
    if(!list.length){target.textContent='No current sector observations.';return}
    for(const x of list){
      const de=x.latest?.Germany,eu=x.latest?.EU27,m=x.momentum_4q_change?.Germany,spread=x.germany_vs_eu_spread;
      const row=document.createElement('div');row.className='rawRow';
      const a=document.createElement('b'),b=document.createElement('span'),c=document.createElement('b'),d=document.createElement('span');
      a.textContent=x.dimension_label||x.dimension_key;
      b.textContent=`DE ${de?`${Number(de.value).toFixed(1)}% · ${de.period}`:'—'} · EU ${eu?`${Number(eu.value).toFixed(1)}% · ${eu.period}`:'—'}`;
      c.textContent=metric==='vacancy'?`DE–EU ${spread==null?'—':`${spread>0?'+':''}${Number(spread).toFixed(1)} pp`}`:`YoY ${de?`${Number(de.value).toFixed(1)}%`:'—'}`;
      d.textContent=`${metric==='vacancy'?'4Q vacancy change':'4Q growth-rate change'}: ${m==null?'—':`${m>0?'+':''}${Number(m).toFixed(1)} pp`}`;
      row.append(a,b,c,d);target.appendChild(row);
    }
  }
  function renderLabor(labor,db){
    const table=document.querySelector('.tablePanel');if(!table||!labor)return;
    const section=document.createElement('section');section.className='sectionGrid';section.id='laborIntelligenceSection';
    const vacancy=document.createElement('div');vacancy.className='panel';
    const vh=document.createElement('h2');vh.textContent='Labor demand pressure';
    const vs=document.createElement('div');vs.className='sub';vs.textContent='Official job vacancy rates by sector · Germany vs EU · evidence only, not a ranking input.';
    const vlist=document.createElement('div');vlist.className='rawList';vlist.style.marginTop='12px';addLaborRows(vlist,labor.sectors,'vacancy');vacancy.append(vh,vs,vlist);
    const cost=document.createElement('div');cost.className='panel';
    const ch=document.createElement('h2');ch.textContent='Labor cost pressure';
    const cs=document.createElement('div');cs.className='sub';cs.textContent='Nominal hourly labor-cost growth by sector · separate NACE mapping · evidence only.';
    const clist=document.createElement('div');clist.className='rawList';clist.style.marginTop='12px';addLaborRows(clist,labor.labor_cost_sectors,'cost');cost.append(ch,cs,clist);
    section.append(vacancy,cost);table.parentNode.insertBefore(section,table);
    const note=document.createElement('div');note.className='info';note.style.margin='0 0 18px';const mapped=(labor.node_signals||[]).length;note.textContent=`Labor intelligence: ${labor.sector_count||0} vacancy sectors, ${labor.labor_cost_sector_count||0} labor-cost sectors, ${mapped} opportunity nodes mapped. These signals are observational evidence only; rankings remain unchanged until the scoring methodology is explicitly validated.`;section.parentNode.insertBefore(note,table);
  }
  const db=await getJSON('./data/latest.json');renderHero(db);if(syncChip)syncChip.textContent='Data: static live snapshot';window.startCapitalDashboard(db);
  try{
    const st=await getJSON('./data/status.json');
    if(statusEl){statusEl.textContent='';const strong=document.createElement('b');strong.textContent=st.mode||'zero-cost static live';statusEl.append(strong,document.createTextNode(` · generated ${fmtDate(st.generated_at)} · latest evidence ${st.evidence_updated_at||db.updated||'—'}. Scheduled jobs update files; the frontend itself does not need rebuilding.`))}
    if(lastRefreshChip)lastRefreshChip.textContent=`Refresh: ${fmtDate(st.last_run?.completed_at)}`;
    if(reviewQueueChip)reviewQueueChip.textContent=`Review queue: ${st.pending_review??0}`;
    if(discoveryChip)discoveryChip.textContent=`New discoveries: ${st.new_discovered_items??0}`;
    if(snapshotCountChip)snapshotCountChip.textContent=`Snapshots: ${st.snapshot_count??0}`;
    if(sourceCountChip)sourceCountChip.textContent=`Evidence sources: ${st.source_count??(db.sources||[]).length}`;
    if(syncChip)syncChip.textContent='Data: Git-backed static live';
  }catch(e){if(statusEl)statusEl.textContent='Static data status unavailable: '+e.message}
  try{
    const rows=await getJSON('./data/signals-latest.json');renderSignals(rows);
    const st=await getJSON('./data/signal-status.json');if(signalStatus)signalStatus.textContent=`${st.observation_count||0} stored raw observation(s), ${st.current_observation_count||0} current. Latest collector: ${st.last_collector||'—'} · ${st.last_run_status||'—'}.`;if(signalCountChip)signalCountChip.textContent=`Signal observations: ${st.observation_count||0}`;if(signalRunChip)signalRunChip.textContent=`Signal refresh: ${fmtDate(st.last_run_at)}`;
  }catch(e){if(liveSignals)liveSignals.textContent='Structured signal files have not been generated yet.';if(signalStatus)signalStatus.textContent=e.message}
  try{renderLabor(await getJSON('./data/labor-intelligence.json'),db)}catch(e){console.warn('Labor intelligence unavailable:',e)}
  let hist=[];
  try{hist=await getJSON('./data/history-index.json');historyFrom.textContent='';historyTo.textContent='';if(!hist.length){historySummary.textContent='No snapshots yet.';historyCompare.disabled=true}else{hist.forEach(x=>{option(historyFrom,x);option(historyTo,x)});historyTo.value=hist[0].id;historyFrom.value=(hist[1]||hist[0]).id;historyCompare.disabled=hist.length<2;historySummary.textContent=hist.length<2?'One snapshot exists. A later validated dataset will create comparison history.':'Choose two snapshots and compare validated changes.'}}catch(e){historySummary.textContent='History unavailable: '+e.message;historyCompare.disabled=true}
  if(historyCompare)historyCompare.onclick=async()=>{if(!historyFrom.value||!historyTo.value)return;historyCompare.disabled=true;historySummary.textContent='Comparing…';try{const [a,b]=await Promise.all([getJSON(`./data/history/${encodeURIComponent(historyFrom.value)}.json`),getJSON(`./data/history/${encodeURIComponent(historyTo.value)}.json`)]);renderDiff(compareSnapshots(a,b))}catch(e){historySummary.textContent='Could not compare snapshots: '+e.message}finally{historyCompare.disabled=false}};
})().catch(err=>{const el=document.getElementById('liveStatus');if(el)el.textContent='Could not load dashboard data: '+err.message;console.error(err)});
