# Deployment

Local: Python 3.11 venv + `pip install -e '.[dev]'`, `cp .env.example .env`, `python -m scripts.ingest_documents`, `uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`, then `cd frontend && npm install && npm run dev`. Frontend Vite proxies `/api` to the local FastAPI port.

Compose: build a Python backend and nginx-hosted React bundle, with Chroma/SQLite/uploads persisted in the `rag_runtime` volume. `docker compose up --build` serves the UI on `127.0.0.1:8080`; backend has no public published port. The Docker images require online installation/model cache setup. The image runs as an unprivileged user with writable runtime. The default Compose startup does not ingest documents automatically; index them explicitly.

Production changes: set a nonempty `ADMIN_TOKEN` and use a reverse proxy to provide authenticated and authorized user access (the UI accepts an in-memory token in the sidebar); TLS with trusted certificate; correct CORS; upstream upload caps; a private DNS/egress layer; CDN/cache for static assets only; process and disk quotas; secrets management, index snapshots/backups and restore testing; proper readiness probe with vector/model initialization; worker sizing for CPU model loading; and an async queue if indexing becomes a long-running workload. Do not expose this reference implementation as an open anonymous multi-user SaaS.

Validation sequence: `pytest`, lint, frontend build, ingest sample docs, retrieval smoke check, authenticated provider model check, 2-turn answer-with-citations test, export evaluation JSON and manually verify excerpts. Health HTTP 200 is liveness, not proof that the remote Groq model is reachable.
