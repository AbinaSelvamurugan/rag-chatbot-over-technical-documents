from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
import ipaddress
import logging
import os
import socket
import threading
import time
import httpx
from .chunking import chunk_segments
from .extraction import extract, EXTENSIONS
from .registry import Registry
from .vectorstore import VectorStore
from ..core.config import Settings

log = logging.getLogger(__name__)

class Ingestion:
    def __init__(self, settings: Settings, registry: Registry, index: VectorStore):
        self.cfg, self.registry, self.index = settings, registry, index
        self.lock = threading.RLock()

    def ingest(self, name: str, data: bytes, collection: str='default', uri: str | None=None,
               replace_id: str | None=None) -> dict:
        if len(data) > self.cfg.max_upload_mb * 1024 * 1024:
            raise ValueError('Upload exceeds size limit')
        if Path(name).suffix.lower() not in EXTENSIONS:
            raise ValueError('Unsupported file type')
        if self.cfg.chunk_overlap >= self.cfg.chunk_size:
            raise ValueError('Chunk overlap must be smaller than size')
        digest = sha256(data).hexdigest()
        with self.lock:
            existing = self.registry.by_hash(collection,digest)
            if existing and existing['id'] != replace_id:
                return {**existing, 'duplicate': True}
            started=time.perf_counter()
            document_id = replace_id or sha256(f'{collection}\0{digest}'.encode()).hexdigest()[:32]
            now = time.time()
            path = self.cfg.data_dir / 'uploads' / (document_id + Path(name).suffix.lower())
            record = dict(id=document_id,collection=collection,title=Path(name).name,
                          uri=uri,source_type='url' if uri else Path(name).suffix.lower().lstrip('.'),
                          content_hash=digest, location=str(path),version=None,status='indexing',
                          error=None,chunks=0,created_at=now,updated_at=now,extraction_chars=0,duration_ms=0)
            # Parse and chunk before altering an existing healthy index.
            try:
                segments=extract(name,data)
                chunks=chunk_segments(document_id,segments,self.cfg.chunk_size,self.cfg.chunk_overlap)
                if not chunks: raise ValueError('No useful chunks produced')
                if len(chunks) > self.cfg.max_chunks: raise ValueError('Too many chunks')
                path.parent.mkdir(parents=True,exist_ok=True)
                temp=path.with_suffix(path.suffix + '.tmp')
                temp.write_bytes(data)
                os.replace(temp,path)
                rows=[]
                for c in chunks:
                    meta={'document_id':document_id,'scope':collection,'source_title':name,
                          'source_type':record['source_type'],'content_hash':digest,
                          'ingestion_timestamp':str(now),'chunk_id':c.id}
                    if uri: meta['source_uri']=uri
                    if c.page is not None: meta['page_number']=c.page
                    if c.section: meta['section_title']=c.section
                    rows.append({'id':c.id,'text':c.text,'metadata':meta})
                self.index.add(rows)
                # Remove stale vectors after successful new index write.
                new_ids={c.id for c in chunks}
                previous=self.index.get_doc(document_id)
                old_ids=[i for i in previous['ids'] if i not in new_ids]
                if old_ids: self.index.collection.delete(ids=old_ids)
                record.update(status='indexed',chunks=len(chunks),extraction_chars=sum(len(s.text) for s in segments),
                              duration_ms=round((time.perf_counter()-started)*1000,2))
                self.registry.put(record)
                log.info('document_indexed id=%s chunks=%s duration_ms=%s',document_id,len(chunks),record['duration_ms'])
                return {**record,'duplicate':False}
            except Exception as exc:
                # New documents must never leave selectable orphan vectors after a partial batch upsert.
                if not replace_id:
                    try: self.index.remove(document_id)
                    except Exception: log.warning('orphan_cleanup_failed id=%s',document_id)
                if not replace_id:
                    record.update(status='failed', error=str(exc)[:200])
                    self.registry.put(record)
                log.warning('document_index_failed id=%s error=%s',document_id,type(exc).__name__)
                raise

    def reindex(self, doc_id: str) -> dict:
        doc=self.registry.get(doc_id)
        if not doc: raise KeyError('Document not found')
        path=Path(doc['location'])
        if not path.is_file(): raise ValueError('Original bytes unavailable for re-index')
        return self.ingest(doc['title'],path.read_bytes(),doc['collection'],doc['uri'],replace_id=doc_id)

    def delete(self, doc_id: str):
        with self.lock:
            doc=self.registry.get(doc_id)
            if not doc: raise KeyError('Document not found')
            self.index.remove(doc_id)
            self.registry.delete(doc_id)
            if doc['location']:
                Path(doc['location']).unlink(missing_ok=True)

    def reset_collection(self, collection: str) -> int:
        # Explicit destructive operation. Does not reset the underlying Chroma collection or other scopes.
        with self.lock:
            records=self.registry.list(collection)
            for document in records:
                self.delete(document['id'])
            return len(records)


def validate_url(url: str, cfg: Settings):
    url_parts=urlparse(url)
    hostname=(url_parts.hostname or '').lower()
    if url_parts.scheme != 'https' or url_parts.username or url_parts.password or url_parts.port not in (None,443):
        raise ValueError('Only standard HTTPS URLs without credentials are permitted')
    if not cfg.allow_url_ingestion or hostname not in cfg.hosts:
        raise ValueError('URL ingestion is disabled or host is not approved')
    try:
        addresses=socket.getaddrinfo(hostname,443,type=socket.SOCK_STREAM)
        if not addresses: raise ValueError('DNS resolution returned no addresses')
        for a in addresses:
            ip=ipaddress.ip_address(a[4][0])
            if not ip.is_global: raise ValueError('URL resolves to a non-public IP')
    except OSError as exc:
        raise ValueError('Host cannot be resolved') from exc


def fetch_url(url: str, cfg: Settings) -> tuple[str,bytes]:
    # Strict host allowlist, no redirects, no proxy env, bounded downloads.
    validate_url(url,cfg)
    from urllib.robotparser import RobotFileParser
    parsed=urlparse(url)
    root=f'{parsed.scheme}://{parsed.netloc}'
    with httpx.Client(follow_redirects=False,timeout=httpx.Timeout(12.0),trust_env=False) as client:
        robots=client.get(root + '/robots.txt')
        if robots.status_code != 200:
            raise ValueError('Cannot verify robots.txt permissions for this host')
        parser=RobotFileParser()
        parser.parse(robots.text.splitlines())
        if not parser.can_fetch('TechnicalDocsAI/1.0',url):
            raise ValueError('robots.txt does not permit this URL')
        with client.stream('GET', url, headers={'User-Agent':'TechnicalDocsAI/1.0 (user-initiated; respectful)'}) as response:
            if response.status_code != 200: raise ValueError(f'Document server returned HTTP {response.status_code}')
            mime=response.headers.get('content-type','').split(';')[0].strip()
            suffix={ 'text/html':'.html','application/pdf':'.pdf','text/plain':'.txt','text/markdown':'.md'}.get(mime)
            if suffix is None: raise ValueError('Unsupported source MIME type')
            buffer=bytearray()
            for part in response.iter_bytes(65536):
                buffer.extend(part)
                if len(buffer)>cfg.max_upload_mb*1024*1024:
                    raise ValueError('URL document exceeds size limit')
            filename=Path(parsed.path).name or 'documentation'
            if not filename.lower().endswith(suffix): filename += suffix
            return filename,bytes(buffer)
