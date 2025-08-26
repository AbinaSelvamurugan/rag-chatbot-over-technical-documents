import {useCallback,useEffect,useRef,useState} from 'react';
import {BookOpen,BrainCircuit,ChevronDown,ChevronRight,Clipboard,Database,ExternalLink,File,FileText,LoaderCircle,MessageSquare,Plus,RefreshCcw,Search,Send,ShieldCheck,Square,Trash2,X,Activity,BarChart3,Link2,Settings2} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {api} from './services/api';
import type {Answer,DocumentRecord,Message,Passage,Scope} from './types';

function niceError(error:unknown){return error instanceof Error?error.message:String(error)}
function short(text:string,size=44){return text.length>size?text.slice(0,size)+'…':text}
function date(value:number){return new Date(value*1000).toLocaleDateString()}
function Citation({passage,onClick}:{passage:Passage;onClick:()=>void}){return <button className="cite" onClick={onClick} title={`Inspect ${passage.title}`}>[{passage.citation_id}]</button>}

export default function App(){
  const [token,setToken]=useState('');
  const client=api(token);
  const [tab,setTab]=useState<'chat'|'documents'|'evaluation'>('chat');
  const [documents,setDocuments]=useState<DocumentRecord[]>([]);
  const [config,setConfig]=useState<{embedding_model:string;groq_model:string|null;index_name:string;llm_configured:boolean}|null>(null);
  const [health,setHealth]=useState('checking');
  const [scopes,setScopes]=useState<string[]>(['default']);
  const [scope,setScope]=useState<Scope>({collection:'default',document_ids:[]});
  const [session,setSession]=useState<string|null>(null);
  const [messages,setMessages]=useState<Message[]>([]);
  const [question,setQuestion]=useState('');
  const [busy,setBusy]=useState(false);
  const [status,setStatus]=useState('');
  const [error,setError]=useState('');
  const [uploading,setUploading]=useState(false);
  const [url,setUrl]=useState('');
  const [sources,setSources]=useState<Passage[]>([]);
  const [activeSource,setActiveSource]=useState<string|null>(null);
  const [trace,setTrace]=useState<Answer['trace']|null>(null);
  const [metrics,setMetrics]=useState<{questions:number;run_id:string;macro_document_metrics:Record<string,number>}|null>(null);
  const [pendingOp,setPendingOp]=useState('');
  const controller=useRef<AbortController|null>(null);
  const end=useRef<HTMLDivElement|null>(null);
  const picker=useRef<HTMLInputElement|null>(null);

  const refresh=useCallback(async()=>{
    const a=api(token);
    const [ds,cs,cf,h]=await Promise.allSettled([a.documents(),a.collections(),a.config(),a.health()]);
    if(ds.status==='fulfilled')setDocuments(ds.value);else setError(niceError(ds.reason));
    if(cs.status==='fulfilled')setScopes(cs.value.scopes);
    if(cf.status==='fulfilled')setConfig(cf.value);
    if(h.status==='fulfilled')setHealth(h.value.status);else setHealth('offline');
  },[token]);
  useEffect(()=>{void refresh()},[refresh]);
  useEffect(()=>{end.current?.scrollIntoView({behavior:'smooth'})},[messages,busy]);

  async function clearConversation(){
    controller.current?.abort();setBusy(false);
    if(session)try{await client.clear(session)}catch(e){setError(niceError(e))}
    setMessages([]);setSession(null);setSources([]);setTrace(null);setActiveSource(null);
  }
  function changeScope(next:Scope){void clearConversation();setScope(next)}
  async function ask(){
    const q=question.trim();if(!q||busy)return;
    setQuestion('');setError('');setBusy(true);setStatus('Retrieving and validating evidence');
    setMessages(m=>[...m,{role:'user',text:q}]);
    const abort=new AbortController();controller.current=abort;
    try{
      const answer=await client.chat(q,scope,session,abort.signal);
      setSession(answer.session_id);setMessages(m=>[...m,{role:'assistant',text:answer.answer,answer}]);
      setSources(answer.sources);setTrace(answer.trace);setActiveSource(null);
    }catch(e){
      if(!abort.signal.aborted){setError(niceError(e));setMessages(m=>[...m,{role:'assistant',text:'Answer unavailable. No answer was returned.'}])}
    }finally{setBusy(false);setStatus('');controller.current=null}
  }
  async function inspect(){
    const q=question.trim()||messages.filter(m=>m.role==='user').at(-1)?.text;
    if(!q)return setError('Enter a question first.');
    setError('');setPendingOp('retrieve');
    try{const out=await client.retrieve(q,scope);setSources(out.candidates);setTrace({candidate_count:out.candidates.length,selected_count:out.selected.length,retrieval_ms:out.retrieval_ms,llm_ms:0,retrieval_query:q,all_candidates:out.candidates});setTab('chat')}
    catch(e){setError(niceError(e))}finally{setPendingOp('')}
  }
  async function upload(files:FileList|null){
    if(!files?.length)return;setUploading(true);setError('');
    for(const file of Array.from(files)){
      try{await client.upload(file,scope.collection)}catch(e){setError(`${file.name}: ${niceError(e)}`)}
    }
    setUploading(false);await refresh();
    if(picker.current)picker.current.value='';
  }
  async function ingestUrl(){
    if(!url.trim())return;setPendingOp('url');setError('');
    try{await client.ingestUrl(url.trim(),scope.collection);setUrl('');await refresh()}
    catch(e){setError(niceError(e))}finally{setPendingOp('')}
  }
  async function op(id:string,type:'delete'|'reindex'){
    if(type==='delete'&&!window.confirm('Delete this document and all of its indexed chunks?'))return;
    setPendingOp(id);setError('');
    try{if(type==='delete')await client.delete(id);else await client.reindex(id);await refresh()}
    catch(e){setError(niceError(e))}finally{setPendingOp('')}
  }
  async function downloadOriginal(source:Passage){
    try{
      const blob=await client.original(source.document_id);
      const location=URL.createObjectURL(blob);
      const link=document.createElement('a');link.href=location;link.download=source.title;
      document.body.append(link);link.click();link.remove();URL.revokeObjectURL(location);
    }catch(e){setError(niceError(e))}
  }
  async function resetCollection(){
    const expected=`DELETE ${scope.collection}`;
    const confirmation=window.prompt(`This deletes all indexed documents in ${scope.collection}. Type ${expected} to confirm:`);
    if(confirmation!==expected)return;
    setPendingOp('reset');setError('');
    try{await client.resetCollection(scope.collection,confirmation);await clearConversation();await refresh()}
    catch(e){setError(niceError(e))}finally{setPendingOp('')}
  }
  async function runEvaluation(){setPendingOp('eval');setError('');try{setMetrics(await client.evaluate())}catch(e){setError(niceError(e))}finally{setPendingOp('')}}
  const shownDocs=documents.filter(d=>d.collection===scope.collection);
  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-icon"><BrainCircuit size={22}/></div><div><strong>TechnicalDocs <span>AI</span></strong><small>GROUND TRUTH STUDIO</small></div></div>
      <div className="nav-title">WORKSPACE</div>
      <nav aria-label="Primary"><button onClick={()=>setTab('chat')} className={tab==='chat'?'active':''}><MessageSquare size={17}/> Ask documentation</button><button onClick={()=>setTab('documents')} className={tab==='documents'?'active':''}><FileText size={17}/> Knowledge base <span className="nav-count">{documents.filter(d=>d.status==='indexed').length}</span></button><button onClick={()=>setTab('evaluation')} className={tab==='evaluation'?'active':''}><BarChart3 size={17}/> Evaluation lab</button></nav>
      <div className="side-group"><div className="nav-title">CURRENT COLLECTION</div><label className="sr-only" htmlFor="collection">Collection</label><select id="collection" value={scope.collection} onChange={e=>changeScope({collection:e.target.value,document_ids:[]})}>{[...new Set([scope.collection,...scopes])].map(s=><option key={s} value={s}>{s}</option>)}</select></div>
      <div className="side-group"><div className="nav-title">SCOPE DOCUMENTS</div><div className="scope-list">{shownDocs.filter(d=>d.status==='indexed').map(d=><label key={d.id} className="scope-doc"><input type="checkbox" checked={scope.document_ids.includes(d.id)} onChange={e=>{const next=e.target.checked?[...scope.document_ids,d.id]:scope.document_ids.filter(x=>x!==d.id);changeScope({...scope,document_ids:next})}}/><span title={d.title}>{short(d.title,27)}</span></label>)}{!shownDocs.some(d=>d.status==='indexed')&&<p className="small-muted">No indexed documents yet.</p>}</div><p className="scope-hint">No selection = all documents in this collection.</p></div>
      <div className="sidebar-bottom"><label className="token-label" htmlFor="admin-token">ADMIN ACCESS TOKEN</label><input id="admin-token" type="password" className="token-input" autoComplete="off" placeholder="Optional for local use" value={token} onChange={e=>setToken(e.target.value)} /><div className="status-line"><span className={`status-dot ${health==='ready'?'good':'warn'}`}/>{health==='ready'?'Services available':health==='checking'?'Checking services':'Degraded / offline'}</div><div className="side-foot"><ShieldCheck size={15}/> Evidence-based answers only</div></div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="bread">WORKSPACE <ChevronRight size={13}/> <b>{tab==='chat'?'Question answering':tab==='documents'?'Document inventory':'Retrieval evaluation'}</b></div><div className="header-actions"><span className="index-chip"><Database size={14}/>{config?.index_name||'Index'}</span><button className="icon-button" aria-label="Set admin token" title="Set admin token" onClick={()=>{const next=window.prompt('Enter admin token (stored in memory only):',token);if(next!==null)setToken(next)}}><ShieldCheck size={16}/></button><button className="icon-button" aria-label="Refresh" title="Refresh status" onClick={()=>void refresh()}><RefreshCcw size={16}/></button></div></header>
      {error&&<div className="error" role="alert"><span>{error}</span><button onClick={()=>setError('')} aria-label="Dismiss error"><X size={15}/></button></div>}
      {tab==='chat'?<div className="chat-layout"><section className="conversation" aria-label="Conversation"><div className="messages">
        {!messages.length&&<div className="welcome"><div className="hero-symbol"><BookOpen size={30}/></div><div className="eyebrow">TECHNICAL KNOWLEDGE, VERIFIED</div><h1>Answers you can <em>trace.</em></h1><p>Ask a question about your indexed technical documents. Every supported claim points to a passage you can inspect.</p><div className="suggestions"><button onClick={()=>setQuestion('What is the difference between operational and configuration mode?')}>Operational vs configuration mode <ChevronRight size={14}/></button><button onClick={()=>setQuestion('How can I safely review configuration changes?')}>Reviewing configuration changes <ChevronRight size={14}/></button><button onClick={()=>setQuestion('What documentation supports troubleshooting interface status?')}>Troubleshooting interface status <ChevronRight size={14}/></button></div></div>}
        {messages.map((m,i)=><div key={i} className={'message '+m.role}><div className="message-label">{m.role==='user'?'YOU':'TECHNICALDOCS AI'}</div><div className="message-content">{m.role==='user'?<p>{m.text}</p>:m.answer&&!m.answer.abstained?<>{m.answer.claims.map((claim,j)=><div key={j} className="claim"><ReactMarkdown remarkPlugins={[remarkGfm]}>{claim.text}</ReactMarkdown>{claim.source_ids.map(id=>{const src=m.answer!.sources.find(s=>s.citation_id===id);return src?<Citation key={id} passage={src} onClick={()=>{setSources(m.answer!.sources);setTrace(m.answer!.trace);setActiveSource(src.chunk_id)}}/>:null})}</div>)}</>:<ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>}</div>{m.answer&&<div className="answer-meta"><span>{m.answer.abstained?'Insufficient evidence':'Citations checked'}</span><span>{m.answer.trace.selected_count} passages</span><span>{m.answer.latency_ms.toFixed(0)} ms</span><button onClick={()=>void navigator.clipboard.writeText(m.text)}><Clipboard size={13}/> Copy</button></div>}</div>)}
        {busy&&<div className="loading" role="status"><LoaderCircle size={18} className="spin"/> {status}</div>}<div ref={end}/>
      </div><div className="composer"><div className="composer-tools"><span><ShieldCheck size={14}/> GROUNDED MODE</span><button onClick={()=>void clearConversation()}><Trash2 size={14}/> Clear conversation</button></div><div className="input-wrap"><label htmlFor="prompt" className="sr-only">Question</label><textarea id="prompt" rows={3} placeholder="Ask a technical question about your documents..." value={question} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();void ask()}}}/><div className="composer-bottom"><button className="ghost" onClick={()=>void inspect()} disabled={!!pendingOp}><Search size={15}/> Inspect retrieval</button>{busy?<button className="primary stop" onClick={()=>controller.current?.abort()}><Square size={14}/> Cancel</button>:<button className="primary" onClick={()=>void ask()} disabled={!question.trim()}><Send size={16}/> Send question</button>}</div></div><p className="disclaimer">Answers require verified indexed evidence. Source text is not treated as instructions.</p></div></section>
        <aside className="evidence" aria-label="Retrieved evidence"><div className="panel-heading"><div><div className="eyebrow">TRANSPARENCY</div><h2>Evidence inspector</h2></div><span className="panel-count">{sources.length}</span></div><div className="evidence-body">{trace&&<div className="trace-card"><div className="trace-title"><Activity size={15}/> Retrieval trace</div><div className="trace-stats"><span><b>{trace.candidate_count}</b> candidates</span><span><b>{trace.selected_count}</b> selected</span><span><b>{trace.retrieval_ms.toFixed(0)}ms</b> search</span></div><div className="tiny muted">Query: {short(trace.retrieval_query,180)}</div></div>}{!sources.length&&<div className="evidence-empty"><Search size={30}/><strong>No sources retrieved</strong><p>Run a question or inspect retrieval to see the retrieved source passages.</p></div>}{sources.map(s=><div key={s.chunk_id} className={'source-card '+(activeSource===s.chunk_id?'expanded':'')}><button className="source-open" onClick={()=>setActiveSource(activeSource===s.chunk_id?null:s.chunk_id)}><span className="source-rank">{s.citation_id}</span><span className="source-title"><strong>{s.title}</strong><small>{s.page_number?`Page ${s.page_number}`:s.section||'Source excerpt'} · Rank {s.rank}</small></span>{activeSource===s.chunk_id?<ChevronDown size={15}/>:<ChevronRight size={15}/>}</button><p className="source-preview">{short(s.text.replace(/\s+/g,' '),145)}</p>{activeSource===s.chunk_id&&<div className="source-detail"><div className="tiny">Distance: {s.distance===null?'n/a':s.distance.toFixed(4)} (not confidence)</div><pre>{s.text}</pre>{s.uri?<a href={s.uri} target="_blank" rel="noopener noreferrer">Open original source <ExternalLink size={13}/></a>:<button className="source-download" onClick={()=>void downloadOriginal(s)}>Download uploaded original <ExternalLink size={13}/></button>}<span className="tiny">Chunk: {s.chunk_id}</span></div>}</div>)}</div></aside></div>:
      tab==='documents'?<div className="page"><div className="page-heading"><div><div className="eyebrow">KNOWLEDGE OPERATIONS</div><h1>Document library</h1><p>Index, inspect and manage provenance for each source.</p></div><button className="primary" onClick={()=>picker.current?.click()} disabled={uploading}><Plus size={16}/>{uploading?'Indexing...':'Add documents'}</button><input type="file" hidden multiple accept=".pdf,.md,.txt,.html,.htm" ref={picker} onChange={e=>void upload(e.target.files)}/></div><div className="stat-grid"><div><span>Indexed sources</span><strong>{documents.filter(d=>d.status==='indexed').length}</strong></div><div><span>Indexed chunks</span><strong>{documents.filter(d=>d.status==='indexed').reduce((a,d)=>a+d.chunks,0)}</strong></div><div><span>Embedding model</span><strong className="model-name">{config?.embedding_model||'Unavailable'}</strong></div></div><div className="url-panel"><div><h3><Link2 size={17}/> Permitted source URL</h3><p>Disabled by default. Enable the host allowlist and robots checks on the backend.</p></div><div className="url-input"><input type="url" value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://www.juniper.net/documentation/..." aria-label="Source URL"/><button onClick={()=>void ingestUrl()} disabled={pendingOp==='url'||!url.trim()}>Index URL</button></div></div><div className="table-card"><div className="table-title"><h3>Source inventory</h3><button onClick={()=>void refresh()}><RefreshCcw size={14}/> Refresh</button></div><div className="table-scroll"><table><thead><tr><th>DOCUMENT</th><th>COLLECTION</th><th>STATUS</th><th>CHUNKS</th><th>UPDATED</th><th>ACTIONS</th></tr></thead><tbody>{documents.map(d=><tr key={d.id}><td><span className="doc-cell"><File size={17}/><span><b>{d.title}</b><small>{d.source_type.toUpperCase()} · {d.extraction_chars} characters{d.error?' · '+d.error:''}</small></span></span></td><td>{d.collection}</td><td><span className={'doc-status '+d.status}>{d.status}</span></td><td>{d.chunks}</td><td>{date(d.updated_at)}</td><td><div className="row-actions"><button title="Re-index" aria-label={`Re-index ${d.title}`} disabled={!!pendingOp} onClick={()=>void op(d.id,'reindex')}><RefreshCcw size={15}/></button><button title="Delete" aria-label={`Delete ${d.title}`} disabled={!!pendingOp} onClick={()=>void op(d.id,'delete')}><Trash2 size={15}/></button></div></td></tr>)}{!documents.length&&<tr><td colSpan={6} className="table-empty">No indexed documents. Upload a permitted PDF, HTML, Markdown or text file to get started.</td></tr>}</tbody></table></div></div><div className="danger-zone"><div><strong>Collection administration</strong><p>Permanent deletion of indexed documents in the active collection only.</p></div><button onClick={()=>void resetCollection()} disabled={!!pendingOp}><Trash2 size={15}/> Reset collection</button></div></div>:
      <div className="page eval-page"><div className="page-heading"><div><div className="eyebrow">REPRODUCIBLE RESEARCH</div><h1>Retrieval evaluation</h1><p>Measure retrieval against annotated source relevance.</p></div><button className="primary" disabled={!!pendingOp} onClick={()=>void runEvaluation()}><BarChart3 size={16}/>{pendingOp==='eval'?'Evaluating...':'Run benchmark'}</button></div><div className="url-panel"><div><h3><Settings2 size={17}/> Evaluation settings</h3><p>Dataset: <code>evaluation/dataset/local_questions.json</code> · k=5 · document-level relevance · no LLM generation</p></div></div>{metrics?<><div className="eyebrow results-label">EVALUATION RUN · {metrics.run_id}</div><div className="stat-grid">{Object.entries(metrics.macro_document_metrics).map(([name,value])=><div key={name}><span>{name.replaceAll('_',' ').toUpperCase()}</span><strong>{(value*100).toFixed(1)}%</strong></div>)}</div><p className="muted">{metrics.questions} annotated questions. Corpus must be indexed for meaningful retrieval metrics. Full run details saved in evaluation/results.</p></>:<div className="eval-empty"><BarChart3 size={32}/><h2>No evaluation run loaded</h2><p>Ingest the supplied test corpus, then run the benchmark.</p></div>}</div>}
    </main>
  </div>
}
