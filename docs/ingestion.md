# Ingestion and provenance

`Ingestion.ingest` enforces a size cap and extensions, calculates SHA-256, checks duplicates in a target collection, extracts pages/sections, creates stable chunk IDs, embeds batches, commits upserts to Chroma, and records an indexed status in SQLite **after successful index insertion**. Error states are recorded for new documents. Re-ingesting identical bytes is idempotent by hash.

PDFs are parsed using `pypdf.PdfReader` and return 1-based PDF page positions. Scans with no text are explicitly rejected and require a separately installed OCR workflow. HTML removes nav/scripts/footer and extracts article/main; `<pre>` and table cells remain readable though layout is not guaranteed. Markdown retains headings and fenced examples. UTF-8 text decoding errors, binary NUL bytes and malformed PDFs raise clear errors.

Chunk sizes are approximate characters, not tokens. `CHUNK_SIZE` and `CHUNK_OVERLAP` apply within heading sections, with the heading copied into subchunks for embedding context. Inputs above the upper chunk count or upload limits fail explicitly. Metadata includes content checksum, chunk ID, source title/type/URI, ingestion timestamp and optional page or section metadata. Collection scope is a stable scalar metadata field. SQLite holds the persisted source path, not returned in public document metadata.

Approved HTTPS sources require `ALLOW_URL_INGESTION=true`, exact `ALLOWED_HOSTS`, public DNS resolution, `robots.txt` permission, successful content-type mapping and strict size/time boundaries. No login or crawling. Direct URL fetching can still be exposed to DNS rebinding; enforce network egress controls before deployment.

Example: `python -m scripts.ingest_documents --dir data/sample_documents`. For collection partitioning: `--collection my-team` and matching UI scope. A changed embedding signature rejects an incompatible persisted index; create a new validated collection and explicitly re-ingest, never silently mix vectors.
