from __future__ import annotations
import re
from pydantic import BaseModel, Field, ValidationError
from ..schemas import Claim, Passage
from .retrieval import terms

class CitationError(ValueError):
    pass

class ModelAnswer(BaseModel):
    abstain: bool = False
    claims: list[Claim] = Field(default_factory=list,max_length=12)

STOP = {'this','that','with','from','into','have','will','your','then','when','such','also',
        'only','there','which','each','using','they','should','must','where','about','these',
        'their','document','source','following','provided','because','after','before'}


def supports_claim(text: str, excerpt: str) -> bool:
    """Conservative surface-evidence gate, not a semantic entailment proof.
    Fail closed for low lexical overlap, especially technical identifiers.
    """
    q={x for x in terms(text) if len(x)>=4 and x not in STOP}
    evidence=terms(excerpt)
    # Require literal identity for inline code commands/identifiers before accepting paraphrase.
    commands=re.findall(r'`([^`]+)`',text)
    if any(command not in excerpt for command in commands): return False
    if not q: return False
    return len(q & evidence) >= max(1, int(0.50*len(q)+0.999))


def validate_answer(payload: object, passages: list[Passage]) -> list[Claim]:
    try:
        answer=ModelAnswer.model_validate(payload)
    except ValidationError as exc:
        raise CitationError('Malformed structured answer') from exc
    if answer.abstain: return []
    if not answer.claims: raise CitationError('No claims supplied')
    refs={p.citation_id:p for p in passages}
    verified=[]
    for claim in answer.claims:
        if not claim.text.strip() or len(claim.text)>1200 or not claim.source_ids:
            raise CitationError('Claim must have text and source references')
        if len(set(claim.source_ids))!=len(claim.source_ids):
            raise CitationError('Duplicate references in a claim')
        for cid in claim.source_ids:
            if cid not in refs: raise CitationError(f'Unrecognized citation ID: {cid}')
        if not all(supports_claim(claim.text,refs[cid].text) for cid in claim.source_ids):
            raise CitationError('Citation appears unrelated to the claim')
        verified.append(claim)
    return verified


def render_claims(claims: list[Claim]) -> str:
    return '\n\n'.join(c.text.strip()+' '+' '.join(f'[{s}]' for s in c.source_ids) for c in claims)

ABSTENTION='The indexed documentation does not provide enough evidence to answer this question. Try selecting a relevant document or uploading additional permitted documentation.'
