# Project report outline

1. **Abstract:** problem, system scope, methodology and results.
2. **Introduction / problem definition:** scale of technical documentation, evidence failures in non-grounded assistants and source trust.
3. **Related work:** RAG literature, sparse/dense retrieval, sentence embeddings, vector databases, citation verification and prompt injection. Insert citations from published papers.
4. **Requirements:** ingestion formats, security model, functional user stories, latency and correctness quality attributes.
5. **Architecture:** ingestion sequence, persistent registry/index, model integration, access controls, failure recovery and UI data flow.
6. **Methodology:** dataset creation, human provenance review, chunking, embeddings, retrieval, bounded context, JSON claim generation, citation validation and evaluation formulas.
7. **Implementation:** main components, configuration, API contracts, deployment topology and test strategy.
8. **Evaluation:** corpus statistics, annotated ground truth, per-question retrieval results, optional grounded-answer review, citations, errors, ablations and latency/token measurements.
9. **Discussion:** retrieval misses, domain/version mismatch, lexical validator strengths/weaknesses, model variability, data rights, adversarial cases and reproducibility.
10. **Limitations and future work:** OCR, NLI entailment, hybrid BM25, token-aware chunking, human-curated corpus, multi-tenancy, transactional indexing and asynchronous jobs.
11. **Conclusions and references:** only claims supported by tests, measured outputs, and checked original sources.
12. **Appendix:** .env example (no keys), run commands, raw evaluation JSON, relevant screenshots from a running build, annotated document sources and testing logs.
