# Citation validation contract

Every retrieved passage is labeled with a **temporary** ID `S1..Sn` in a single request. The only allowed source membership list is the selected Chroma result set. Evidence passed to Groq includes labeled text and the indexed source metadata. Groq returns JSON with `abstain` and a bounded array of independent `text` / `source_ids` claims, not a free-form essay.

The validator performs schema checks, ensures each non-abstaining claim has references, rejects duplicate/unknown IDs and requires conservative non-stopword overlap with at least one referenced excerpt. The renderer appends verified `[S1]` labels after claims. UI attaches each ID to title, optional section or page, original URL if present and exact excerpt. `/api/sources/{chunk_id}` checks indexed status before returning a stored excerpt. Invalid structured answers fail with an explicit 422, not silent citation substitution.

**Limit:** lexical overlap is neither entailment nor proof of factual faithfulness. A generated statement might share terminology while reversing a condition. For critical device changes, require manual citation review and/or add independent semantic entailment evaluation with a carefully validated threshold. Model repairs are intentionally not performed, to avoid hiding evidence failures. Missing page, section or source-link metadata is shown as absent rather than synthesized.

The stable source ID is the SHA-derived `chunk_id`, **not** the per-turn `S1` label. Historic `S1` labels cannot carry forward to a later answer.
