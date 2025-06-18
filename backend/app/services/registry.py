from __future__ import annotations
import json
import sqlite3
import time
from pathlib import Path
from uuid import uuid4

class Registry:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS docs (
                id TEXT PRIMARY KEY, collection TEXT NOT NULL, title TEXT NOT NULL,
                uri TEXT, source_type TEXT NOT NULL, content_hash TEXT NOT NULL,
                location TEXT, version TEXT, status TEXT NOT NULL,
                error TEXT, chunks INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL,
                updated_at REAL NOT NULL, extraction_chars INTEGER NOT NULL DEFAULT 0,
                duration_ms REAL NOT NULL DEFAULT 0
              );
              CREATE INDEX IF NOT EXISTS idx_docs_scope ON docs(collection,content_hash);
              CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, scope TEXT NOT NULL, updated_at REAL NOT NULL
              );
              CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                role TEXT NOT NULL, text TEXT NOT NULL, created_at REAL NOT NULL
              );
            ''')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA busy_timeout=10000')
        return db

    def list(self, collection: str | None = None) -> list[dict]:
        with self.connect() as db:
            rows = (db.execute('SELECT * FROM docs WHERE collection=? ORDER BY updated_at DESC', (collection,)) if collection
                    else db.execute('SELECT * FROM docs ORDER BY updated_at DESC'))
            return [dict(r) for r in rows]

    def get(self, doc_id: str) -> dict | None:
        with self.connect() as db:
            r = db.execute('SELECT * FROM docs WHERE id=?', (doc_id,)).fetchone()
            return dict(r) if r else None

    def by_hash(self, scope: str, digest: str) -> dict | None:
        with self.connect() as db:
            r = db.execute('SELECT * FROM docs WHERE collection=? AND content_hash=? AND status="indexed"', (scope, digest)).fetchone()
            return dict(r) if r else None

    def put(self, doc: dict):
        fields = list(doc)
        with self.connect() as db:
            db.execute(f'INSERT OR REPLACE INTO docs ({",".join(fields)}) VALUES ({",".join("?" for _ in fields)})', tuple(doc.values()))
            db.commit()

    def update(self, doc_id: str, **changes):
        if not changes: return
        with self.connect() as db:
            db.execute(f'UPDATE docs SET {", ".join(x+"=?" for x in changes)} WHERE id=?', (*changes.values(), doc_id))
            db.commit()

    def delete(self, doc_id: str):
        with self.connect() as db:
            db.execute('DELETE FROM docs WHERE id=?', (doc_id,))
            db.commit()

    def session(self, sid: str | None, scope: dict, ttl_hours: int) -> tuple[str, list[dict]]:
        now = time.time()
        normalized = json.dumps(scope, sort_keys=True)
        with self.connect() as db:
            db.execute('DELETE FROM messages WHERE session_id IN (SELECT id FROM sessions WHERE updated_at<?)', (now-ttl_hours*3600,))
            db.execute('DELETE FROM sessions WHERE updated_at<?', (now-ttl_hours*3600,))
            row = db.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone() if sid else None
            if row and row['scope'] != normalized:
                # Scope changes invalidate old chat context, avoid cross-document bleed.
                db.execute('DELETE FROM messages WHERE session_id=?', (sid,))
                row = None
            if not row:
                sid = str(uuid4())
                db.execute('INSERT INTO sessions VALUES (?,?,?)', (sid, normalized, now))
            else:
                db.execute('UPDATE sessions SET updated_at=? WHERE id=?', (now, sid))
            rows = db.execute('SELECT role,text FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 6', (sid,)).fetchall()
            db.commit()
            return sid, [dict(r) for r in reversed(rows)]

    def append(self, sid: str, question: str, answer: str):
        with self.connect() as db:
            db.executemany('INSERT INTO messages(session_id,role,text,created_at) VALUES(?,?,?,?)',
                           [(sid, 'user', question, time.time()), (sid, 'assistant', answer[:4000], time.time())])
            db.commit()

    def clear_session(self, sid: str):
        with self.connect() as db:
            db.execute('DELETE FROM messages WHERE session_id=?', (sid,))
            db.execute('DELETE FROM sessions WHERE id=?', (sid,))
            db.commit()
