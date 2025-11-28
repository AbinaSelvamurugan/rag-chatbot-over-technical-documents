# Troubleshooting and limitations

| Symptom | Explanation / action |
|---|---|
| `ModuleNotFoundError: chromadb` | Install project runtime dependencies in Python 3.11 environment. |
| Embedding model download fails | Pre-cache model weights using an authorized internet connection; confirm RAM/network. |
| Incompatible embedding signature | Use a new validated index/collection and intentionally re-ingest. Never mix vectors from different models. |
| Empty knowledge base | Ingest files, then inspect `/api/collections` and `/api/retrieve`. Empty questions abstain. |
| PDF extraction reports OCR required | Source is scanned; process it with a separately installed OCR workflow. |
| Groq 503 | Configure key + available model via `/models`; check quota/network and SDK. |
| Citation 422 | A generated claim did not pass structured validation; inspect retrieval rather than trusting raw model text. |
| CORS / browser API failure | Use Vite dev proxy or nginx Compose proxy; verify matching origins and backend health. |
| URL fetch rejected | Confirm explicit host permission, public DNS, robots, content-type, HTTPS and size. |
| Reindex leaves orphan chunks after process failure | Inspect Chroma/SQLite state, restore from backup or reindex after recovering; cross-store writes lack a transaction. |
| UI cannot authenticate when ADMIN_TOKEN is set | Enter the configured token in the UI sidebar (in memory only), or supply an authenticated proxy header. |

Lexical-overlap and entailment checks are useful defense layers, but no RAG deployment can guarantee that every natural-language claim is fully supported from lexical overlap alone. Retrieval quality depends on the configured embedding model, chunking and reranker; tune these against annotated retrieval metrics rather than treating raw distance as calibrated reliability.
