# Evaluation methodology and reproducibility

## Ground truth

`evaluation/dataset/local_questions.json` contains 12 original test questions and document-title relevance annotations for the 3 original fixture documents. The authors reviewed the fixture paragraphs and assigned expected source titles while writing questions, **before running retrieval**. The dataset is not an independently validated research benchmark and should be replaced with blind expert relevance labels for a publication-grade study. Chunk annotations are supported when IDs are known; document relevance is measured separately. Follow-up q10 is evaluated as a standalone retrieval query and is **not** a sequential follow-up benchmark—run a live multi-turn scenario to assess that feature.

## Metrics

For relevance set R and retrieved top k:
- Precision@k: relevant retrieved / k.
- Recall@k: relevant retrieved / |R|, for nonempty R.
- MRR: reciprocal of first relevant rank.
- nDCG@k: discounted binary gains normalized by ideal discounted gains.
- Hit Rate@k: one if at least one relevant item retrieved.

Questions with an empty reference set are tracked as unanswerable and excluded from positive-relevance retrieval metric macro averages. Each result includes the retrieved titles, chunk IDs, category, timed retrieval and all component scores. Default `--generate` is false, avoiding credentials or paid LLM calls. `--generate` calls the Groq API, saves the answer text, citation-ID membership, usage and latency where returned, and checks literal expected phrases. Missing generation access records a per-question error. Literal phrase recall and valid citation IDs are **not** a complete answer-correctness/faithfulness measure.

## Reproducible run

```bash
python -m scripts.ingest_documents --dir data/sample_documents
python -m scripts.evaluate_rag --k 5
python -m scripts.evaluate_rag --k 5 --generate
```

A run writes `evaluation/results/YYYYMMDDTHHMMSSZ-xxxxxx.json`, with `config`, `questions`, `macro_document_metrics` and `entries`. Compare identical question sets and ground-truth labels across experiments. Proposed ablations: k=3/5/8; CHUNK_SIZE=500/1100/1700 with a full controlled re-index per condition; strategy dense/hybrid/mmr; optional CrossEncoder; alternative embedding models with new index names. Existing runner stores one experiment's configuration per invocation; **it does not automatically orchestrate a complete ablation sweep, tune thresholds or reserve an untouched test set**. Separate development and held-out evaluation sets before selecting a winner.

## Human review

For disputed responses, export the answer, retrieved excerpt/metadata, cited claim and question. A reviewer should independently mark citation support (supported/contradicted/unclear), answer correctness, source relevance, expected abstention, omitted caveats, and whether evidence was withheld. Two reviewers with adjudication are recommended. All automated scores require interpretation and cannot be marketed as proof against hallucination.

Latency is measured by wall time in Python for individual retrieval, Groq calls and total request. The model SDK's returned `prompt_tokens`, `completion_tokens`, `total_tokens` are recorded if present. There is **no cost calculation** without independently verified model-specific pricing.
