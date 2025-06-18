from __future__ import annotations
import asyncio
import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from uuid import UUID
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException, Depends, Response, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from .core.config import ROOT,settings
from .schemas import ChatRequest, ChatResponse, RetrievalRequest, UrlRequest, EvaluationRequest, Scope, CollectionResetRequest
from .services.registry import Registry
from .services.vectorstore import EmbeddingService, VectorStore, IndexErrorState
from .services.ingestion import Ingestion,fetch_url
from .services.retrieval import Retriever
from .services.generation import Generator,ProviderError
from .services.citations import CitationError
from .services.rag import RAG
from .services.evaluation import evaluate
from .services.extraction import EXTENSIONS

log=logging.getLogger('technicaldocs')
logging.basicConfig(level=settings().log_level,format='%(asctime)s %(levelname)s %(name)s %(message)s')

@lru_cache
def registry():
    return Registry(settings().registry_path)

@lru_cache
def services():
    cfg=settings()
    model=EmbeddingService(cfg.embedding_model,cfg.embedding_batch_size)
    index=VectorStore(cfg.chroma_dir,cfg.collection_name,model)
    return Ingestion(cfg,registry(),index), Retriever(cfg,index),RAG(cfg,registry(),Retriever(cfg,index),Generator(cfg)),index

app=FastAPI(title='TechnicalDocs AI',version='0.1.0',description='Grounded technical document retrieval and verified citation mapping')
app.add_middleware(CORSMiddleware,allow_origins=settings().origins,allow_credentials=False,
                   allow_methods=['GET','POST','DELETE'],allow_headers=['Content-Type','X-Admin-Token'])


def authorized(x_admin_token: str | None=Header(default=None)):
    key=settings().admin_token
    if key:
        import hmac
        if not x_admin_token or not hmac.compare_digest(key,x_admin_token):
            raise HTTPException(401,'Authentication required')


def stack():
    try: return services()
    except (ImportError,RuntimeError,IndexErrorState,OSError,ValueError) as exc:
        log.error('service_unavailable type=%s',type(exc).__name__)
        raise HTTPException(503,'Embedding/index service unavailable or incompatible. Check dependencies, model download and index settings.') from exc


def fail(exc: Exception):
    if isinstance(exc,KeyError): raise HTTPException(404,'Document not found') from exc
    if isinstance(exc,ProviderError): raise HTTPException(503,str(exc)) from exc
    if isinstance(exc,CitationError): raise HTTPException(422,str(exc)) from exc
    if isinstance(exc,ValueError): raise HTTPException(400,str(exc)[:300]) from exc
    log.exception('unexpected_api_error')
    raise HTTPException(503,'Operation failed. Inspect server logs and retry.') from exc

@app.get('/api/health')
def health():
    try:
        registry()
        import importlib.util
        installed=all(importlib.util.find_spec(p) for p in ('chromadb','sentence_transformers','langchain_core'))
        ready=services.cache_info().currsize>0
        return {'status':'ready' if ready else 'degraded','registry':'accessible',
                'retrieval_ready':ready,'retrieval_dependencies_installed':bool(installed),
                'llm_configured':bool(settings().groq_api_key and settings().groq_model)}
    except Exception:
        raise HTTPException(503,'Registry inaccessible')

@app.get('/api/config',dependencies=[Depends(authorized)])
def config():
    cfg=settings()
    return {'embedding_model':cfg.embedding_model,'groq_model':cfg.groq_model or None,
      'llm_configured':bool(cfg.groq_model and cfg.groq_api_key),'index_name':cfg.collection_name,
      'chunk_size':cfg.chunk_size,'chunk_overlap':cfg.chunk_overlap,
      'retrieval_strategy':cfg.retrieval_strategy,'reranker_model':cfg.reranker_model or None,'retrieval_k':cfg.retrieval_k,'context_k':cfg.context_k,'max_upload_mb':cfg.max_upload_mb,
      'url_ingestion_enabled':cfg.allow_url_ingestion}

@app.get('/api/documents',dependencies=[Depends(authorized)])
def documents(collection: str | None=None):
    records=registry().list(collection)
    for row in records: row.pop('location',None)
    return records

@app.get('/api/documents/{doc_id}',dependencies=[Depends(authorized)])
def document(doc_id: str):
    row=registry().get(doc_id)
    if not row: raise HTTPException(404,'Document not found')
    row.pop('location',None)
    return row

@app.post('/api/documents/upload',dependencies=[Depends(authorized)])
async def upload(file: UploadFile=File(...),collection: str=Form('default')):
    try:
        scope=Scope(collection=collection)
        cap=settings().max_upload_mb*1024*1024
        data=await file.read(cap+1)
        if len(data)>cap: raise HTTPException(413,'Upload exceeds limit')
        name=Path(file.filename or 'unknown').name
        if Path(name).suffix.lower() not in EXTENSIONS: raise HTTPException(400,'Unsupported file type')
        ingest,_,_,_=stack()
        result=await asyncio.to_thread(ingest.ingest,name,data,scope.collection)
        result.pop('location',None)
        return result
    except HTTPException: raise
    except Exception as exc: fail(exc)
    finally: await file.close()

@app.post('/api/documents/url',dependencies=[Depends(authorized)])
def upload_url(req: UrlRequest):
    try:
        name,data=fetch_url(str(req.url),settings())
        ingest,_,_,_=stack()
        result=ingest.ingest(name,data,req.collection,str(req.url))
        result.pop('location',None)
        return result
    except Exception as exc: fail(exc)

@app.get('/api/documents/{doc_id}/original',dependencies=[Depends(authorized)])
def original_document(doc_id: str):
    row=registry().get(doc_id)
    if not row or row['status']!='indexed': raise HTTPException(404,'Document not indexed')
    source=Path(row['location'])
    if not source.is_file(): raise HTTPException(404,'Original bytes unavailable')
    return FileResponse(source,filename=Path(row['title']).name,media_type='application/octet-stream')

@app.post('/api/documents/{doc_id}/reindex',dependencies=[Depends(authorized)])
def reindex(doc_id: str):
    try:
        ingest,_,_,_=stack()
        result=ingest.reindex(doc_id)
        result.pop('location',None)
        return result
    except Exception as exc: fail(exc)

@app.delete('/api/documents/{doc_id}',status_code=204,dependencies=[Depends(authorized)])
def delete(doc_id: str):
    try:
        ingest,_,_,_=stack()
        ingest.delete(doc_id)
        return Response(status_code=204)
    except Exception as exc: fail(exc)

@app.get('/api/collections',dependencies=[Depends(authorized)])
def collections():
    docs=registry().list()
    return {'scopes':sorted(set([d['collection'] for d in docs]+['default'])),
            'indexed_documents':sum(d['status']=='indexed' for d in docs),
            'indexed_chunks':sum(d['chunks'] for d in docs if d['status']=='indexed')}

@app.post('/api/collections/reset',dependencies=[Depends(authorized)])
def reset_collection(req: CollectionResetRequest):
    if req.confirmation != f'DELETE {req.collection}':
        raise HTTPException(400,'Confirmation must equal DELETE followed by collection name')
    try:
        ingest,_,_,_=stack()
        count=ingest.reset_collection(req.collection)
        return {'deleted_documents':count,'collection':req.collection}
    except Exception as exc: fail(exc)

@app.post('/api/retrieve',dependencies=[Depends(authorized)])
def retrieve(req: RetrievalRequest):
    try:
        _,retriever,_,_=stack()
        result=retriever.retrieve(req.question,req.scope,k=req.k)
        return {'retrieval_query':result.query,'retrieval_ms':result.retrieval_ms,
                'candidates':[p.model_dump() for p in result.candidates],
                'selected':[p.model_dump() for p in result.selected]}
    except Exception as exc: fail(exc)

@app.post('/api/chat',response_model=ChatResponse,dependencies=[Depends(authorized)])
def chat(req: ChatRequest):
    try:
        _,_,rag,_=stack()
        return rag.ask(req)
    except Exception as exc: fail(exc)

@app.post('/api/chat/stream',dependencies=[Depends(authorized)])
async def stream_chat(req: ChatRequest, request: Request):
    # Stream protocol emits status and fully validated final answer; never streams unvalidated claims.
    async def events():
        yield 'event: status\ndata: {"phase":"retrieving_and_validating"}\n\n'
        try:
            _,_,rag,_=stack()
            response=await asyncio.to_thread(rag.ask,req)
            if await request.is_disconnected(): return
            yield 'event: answer\ndata: '+response.model_dump_json()+'\n\n'
        except Exception as exc:
            log.warning('stream_error type=%s',type(exc).__name__)
            yield 'event: error\ndata: '+json.dumps({'detail':str(exc) if isinstance(exc,(ProviderError,CitationError,ValueError)) else 'Request failed'})+'\n\n'
    return StreamingResponse(events(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

@app.get('/api/sources/{chunk_id}',dependencies=[Depends(authorized)])
def excerpt(chunk_id: str):
    if not re.fullmatch('[a-f0-9]{24}',chunk_id): raise HTTPException(400,'Invalid chunk ID')
    try:
        _,_,_,index=stack()
        item=index.collection.get(ids=[chunk_id],include=['documents','metadatas'])
        if not item['ids']: raise HTTPException(404,'Excerpt not found')
        meta=item['metadatas'][0]
        document=registry().get(meta['document_id'])
        if not document or document['status']!='indexed': raise HTTPException(404,'Source is not indexed')
        return {'chunk_id':chunk_id,'text':item['documents'][0],'metadata':meta}
    except HTTPException: raise
    except Exception as exc: fail(exc)

@app.delete('/api/sessions/{session_id}',status_code=204,dependencies=[Depends(authorized)])
def clear_session(session_id: str):
    try: UUID(session_id)
    except ValueError: raise HTTPException(400,'Invalid session ID')
    registry().clear_session(session_id)
    return Response(status_code=204)

@app.post('/api/evaluate',dependencies=[Depends(authorized)])
def run_evaluation(req: EvaluationRequest):
    try:
        path=ROOT/'evaluation'/'dataset'/req.dataset
        if not path.is_file(): raise HTTPException(404,'Evaluation dataset not found')
        _,retriever,rag,_=stack()
        return evaluate(path,ROOT/'evaluation'/'results',retriever,rag,req.k,req.generate)
    except HTTPException: raise
    except Exception as exc: fail(exc)
