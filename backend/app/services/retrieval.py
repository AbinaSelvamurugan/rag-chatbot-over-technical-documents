from __future__ import annotations
import re
import time
from dataclasses import dataclass
from .vectorstore import VectorStore
from ..core.config import Settings
from ..schemas import Passage, Scope

WORDS=re.compile(r'[a-zA-Z0-9_.:/-]+')

def terms(text: str) -> set[str]:
    return {x.lower() for x in WORDS.findall(text) if len(x)>=2}


def lexical_score(query: str, passage: str) -> float:
    q=terms(query); p=terms(passage)
    return len(q & p)/len(q) if q else 0.0

@dataclass
class Result:
    candidates: list[Passage]
    selected: list[Passage]
    retrieval_ms: float
    query: str

class Retriever:
    def __init__(self, settings: Settings, index: VectorStore):
        self.cfg,self.index=settings,index
        self.reranker=None

    def retrieve(self, question: str, scope: Scope, k: int | None = None,
                 strategy: str | None=None) -> Result:
        start=time.perf_counter()
        if not question.strip(): raise ValueError('Question must not be empty')
        limit=k or self.cfg.retrieval_k
        strategy=strategy or self.cfg.retrieval_strategy
        if strategy not in ('dense','hybrid','mmr'): raise ValueError('Unknown retrieval strategy')
        rows=self.index.query(question,scope.collection,scope.document_ids,limit)
        if strategy=='hybrid':
            # Candidate fusion: only queries a bounded vector-index window, not an unrestricted corpus.
            # Lexical candidate fusion, not corpus-level BM25. Useful for reordering exact CLI syntax.
            dense_rank={row['id']:i for i,row in enumerate(rows)}
            sparse=sorted(rows,key=lambda row:(-lexical_score(question,row['text']),row['id']))
            sparse_rank={row['id']:i for i,row in enumerate(sparse)}
            rows=sorted(rows,key=lambda row:-(1/(60+dense_rank[row['id']])+1/(60+sparse_rank[row['id']])))
        if strategy=='mmr':
            # Greedy lexical diversity over dense candidates, with a relevance term based on rank.
            pool=rows[:]
            selected=[]
            while pool:
                best=max(pool,key=lambda r:1/(1+rows.index(r))-0.3*max(
                    [lexical_score(r['text'],v['text']) for v in selected] or [0]))
                selected.append(best);pool.remove(best)
            rows=selected
        if self.cfg.reranker_model and rows:
            from sentence_transformers import CrossEncoder
            if self.reranker is None:
                self.reranker=CrossEncoder(self.cfg.reranker_model,trust_remote_code=False)
            scores=self.reranker.predict([(question,row['text']) for row in rows])
            rows=[row for _,row in sorted(zip(scores,rows),key=lambda x:-float(x[0]))]
        passages=[]
        for row in rows:
            if self.cfg.distance_threshold is not None and row['distance']>self.cfg.distance_threshold:
                continue
            m=row['metadata']
            passages.append(Passage(citation_id=f'S{len(passages)+1}',chunk_id=row['id'],
                document_id=m['document_id'],title=m['source_title'],
                uri=m.get('source_uri'),section=m.get('section_title'),
                page_number=m.get('page_number'),text=row['text'],rank=len(passages)+1,
                distance=row['distance'], selected=False))
        chosen=[]; chars=0
        for p in passages:
            if len(chosen)>=self.cfg.context_k: break
            if chars+len(p.text)>self.cfg.max_context_chars: continue
            chosen.append(p.model_copy(update={'selected':True}));chars+=len(p.text)
        return Result(passages,chosen,round((time.perf_counter()-start)*1000,2),question)
