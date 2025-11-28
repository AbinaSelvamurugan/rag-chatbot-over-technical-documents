# Query processing and retrieval

A question is embedded with the same Sentence Transformer model and normalized encoding used during indexing. Chroma retrieves top `RETRIEVAL_K` with collection/document metadata conditions. The optional `DISTANCE_THRESHOLD` accepts raw Chroma **cosine distance**, not a confidence score. `CONTEXT_K` and `MAX_CONTEXT_CHARS` bound the model evidence. Selected passages retain original metadata, candidate rank, score/distance, and exact excerpt.

`RETRIEVAL_STRATEGY=dense` selects native dense rank; `hybrid` reranks only **the dense candidate pool** by reciprocal-rank fusion with lexical overlap. It is not a full lexical index, so exact commands absent from initial dense candidates remain invisible. `mmr` is a simple lexical novelty heuristic over dense candidates rather than embedding-space MMR. `RERANKER_MODEL` can activate a Sentence Transformers CrossEncoder reranker over candidates and incurs model download/runtime overhead. These are optional, not assumed improvements.

For a follow-up containing a short anaphoric reference, the previous user question may be prepended to retrieval text. The query trace retains the original question and the rewritten form; previous model claims are never accepted as evidence. Changing scope invalidates the conversation session. Rank trace is exposed through `/api/retrieve` and the chat response.

Operational queries can fail on exact CLI/identifier matching even when natural-language similarity is high. Tune chunk sizes and candidates against annotated retrieval metrics rather than treating raw distance as calibrated reliability. A blank index returns no passages; `/api/chat` abstains without contacting Groq.
