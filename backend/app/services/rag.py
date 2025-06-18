from __future__ import annotations
from ..schemas import ChatRequest, ChatResponse
import time
from .citations import ABSTENTION
from .generation import Generator
from .registry import Registry
from .retrieval import Retriever
from ..core.config import Settings

class RAG:
    def __init__(self, cfg: Settings, registry: Registry, retriever: Retriever, generator: Generator):
        self.cfg,self.registry,self.retriever,self.generator=cfg,registry,retriever,generator

    def ask(self, req: ChatRequest) -> ChatResponse:
        start=time.perf_counter()
        sid,history=self.registry.session(req.session_id,req.scope.model_dump(),self.cfg.session_ttl_hours)
        # A simple, explicit anaphora resolver; retrieval never uses old assistant claims as evidence.
        question=req.question
        if history and any(x in question.lower().split() for x in ('it','they','that','those','its')):
            previous=next((x['text'] for x in reversed(history) if x['role']=='user'),None)
            if previous: question=f'{previous[:350]}\nFollow-up: {question}'
        result=self.retriever.retrieve(question,req.scope)
        if not result.selected:
            answer,claims,usage,llm_ms,abstained=ABSTENTION,[],{},0.0,True
        else:
            answer,claims,usage,llm_ms,abstained=self.generator.generate(req.question,result.selected,history)
        self.registry.append(sid,req.question,answer)
        return ChatResponse(session_id=sid,answer=answer,claims=claims,abstained=abstained,
            sources=result.selected,trace={'original_query':req.question,'retrieval_query':question,
                'candidate_count':len(result.candidates),'selected_count':len(result.selected),
                'retrieval_ms':result.retrieval_ms,'llm_ms':llm_ms,
                'all_candidates':[p.model_dump() for p in result.candidates]},
            token_usage=usage,latency_ms=round((time.perf_counter()-start)*1000,2))
