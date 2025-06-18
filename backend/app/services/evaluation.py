from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import json
import math
import time
from uuid import uuid4
from ..schemas import Scope,ChatRequest
from .rag import RAG
from .retrieval import Retriever
from .citations import supports_claim


def retrieval_metrics(retrieved: list[str], relevant: set[str], k: int) -> dict[str,float]:
    """Binary document- or chunk-relevance annotated before running evaluation."""
    hits=[1 if item in relevant else 0 for item in retrieved[:k]]
    tp=sum(hits)
    ideal=min(len(relevant),k)
    dcg=sum(h/math.log2(i+2) for i,h in enumerate(hits))
    idcg=sum(1/math.log2(i+2) for i in range(ideal))
    return {'precision_at_k':tp/k,'recall_at_k':tp/len(relevant) if relevant else 0.0,
        'mrr':next((1/(i+1) for i,h in enumerate(hits) if h),0.0),
        'ndcg_at_k':dcg/idcg if idcg else 0.0,'hit_rate_at_k':float(tp>0)}


def evaluate(dataset_path: Path, results_dir: Path, retriever: Retriever, rag: RAG | None,
             k: int=5,generate: bool=False) -> dict:
    data=json.loads(dataset_path.read_text())
    if not isinstance(data.get('questions'),list) or not data['questions']:
        raise ValueError('Dataset has no questions')
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:6]
    entries=[]
    for item in data['questions']:
        scope=Scope(collection=item.get('collection','default'))
        start=time.perf_counter()
        result=retriever.retrieve(item['question'],scope,k=k)
        titles=[p.title for p in result.candidates[:k]]
        chunk_ids=[p.chunk_id for p in result.candidates[:k]]
        doc_metrics=retrieval_metrics(titles,set(item.get('relevant_documents',[])),k)
        chunk_truth=set(item.get('relevant_chunks',[]))
        chunk_metrics=retrieval_metrics(chunk_ids,chunk_truth,k) if chunk_truth else None
        outcome={'id':item['id'],'category':item['category'],'query':item['question'],
                 'retrieved_documents':titles,'retrieved_chunks':chunk_ids,
                 'document_metrics':doc_metrics,'chunk_metrics':chunk_metrics,
                 'retrieval_ms':result.retrieval_ms}
        if generate:
            if rag is None: raise ValueError('RAG service is required for generation evaluation')
            try:
                response=rag.ask(ChatRequest(question=item['question'],scope=scope))
                facts=item.get('expected_facts',[])
                # Deterministic indicator only, NOT a semantic correctness or faithfulness judge.
                matched=sum(bool(f.lower() in response.answer.lower()) for f in facts)
                src_map={p.citation_id:p for p in response.sources}
                unsupported=sum(not all((cid in src_map and supports_claim(claim.text,src_map[cid].text)) for cid in claim.source_ids)
                                for claim in response.claims)
                outcome['answer']={'text':response.answer,'abstained':response.abstained,
                    'abstention_matches_annotation':response.abstained == (not bool(item.get('relevant_documents'))),
                    'surface_unsupported_claims':unsupported,
                    'citation_completeness':all(bool(c.source_ids) for c in response.claims),
                    'all_reference_phrases_present':matched==len(facts) if facts else None,
                    'citation_ids_valid':all(c in {s.citation_id for s in response.sources}
                        for claim in response.claims for c in claim.source_ids),
                    'token_usage':response.token_usage,'latency_ms':response.latency_ms}
            except Exception as exc:
                outcome['answer_error']=f'{type(exc).__name__}: {str(exc)[:160]}'
        outcome['elapsed_ms']=round((time.perf_counter()-start)*1000,2)
        entries.append(outcome)
    keys=('precision_at_k','recall_at_k','mrr','ndcg_at_k','hit_rate_at_k')
    result={'run_id':run_id,'timestamp':datetime.now(timezone.utc).isoformat(),
      'dataset':dataset_path.name,'dataset_annotation_note':data.get('annotation_method','unspecified'),
      'config':{'k':k,'generate':generate,'retrieval_strategy':'dense'},
      'questions':len(entries),
      'macro_document_metrics':{key:sum(e['document_metrics'][key] for e in entries if any(x['id']==e['id'] and x.get('relevant_documents') for x in data['questions']))/max(1,sum(bool(x.get('relevant_documents')) for x in data['questions'])) for key in keys},
      'unanswerable_questions':sum(not x.get('relevant_documents') for x in data['questions']),
      'entries':entries,
      'limitations':'Phrase-match answer check is not an entailment or factual-correctness metric; manual review required.'}
    results_dir.mkdir(parents=True,exist_ok=True)
    (results_dir/f'{run_id}.json').write_text(json.dumps(result,indent=2))
    return result
