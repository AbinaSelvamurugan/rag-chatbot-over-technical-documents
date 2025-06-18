from __future__ import annotations
from pathlib import Path
import hashlib

class IndexErrorState(RuntimeError):
    pass

class EmbeddingService:
    def __init__(self, model_name: str, batch_size: int):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name, trust_remote_code=False)
        self.model_name = model_name
        self.batch_size = batch_size
        dimension=self.model.get_sentence_embedding_dimension()
        if not isinstance(dimension,int) or dimension<=0:
            raise IndexErrorState('Embedding model must return a positive vector dimension')
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts: return []
        return self.model.encode(texts, batch_size=self.batch_size, normalize_embeddings=True,
                                 show_progress_bar=False).tolist()

class VectorStore:
    INDEX_VERSION = '2'
    def __init__(self, path: Path, collection_name: str, embedder: EmbeddingService):
        import chromadb
        path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(path))
        self.embedder = embedder
        signature = hashlib.sha256(f'{embedder.model_name}|normalized|{embedder.dimension}'.encode()).hexdigest()
        metadata = {'model': embedder.model_name, 'dimension': embedder.dimension,
                    'index_version': self.INDEX_VERSION, 'embedding_signature': signature,
                    'hnsw:space': 'cosine'}
        self.collection = self.client.get_or_create_collection(collection_name, metadata=metadata)
        existing = self.collection.metadata or {}
        for key in ['embedding_signature', 'dimension', 'index_version']:
            if existing.get(key) != metadata[key]:
                raise IndexErrorState(f'Index {key} is incompatible; export and re-index using a new collection')

    def add(self, rows: list[dict]):
        for start in range(0, len(rows), self.embedder.batch_size):
            batch = rows[start:start+self.embedder.batch_size]
            vectors = self.embedder.embed([x['text'] for x in batch])
            self.collection.upsert(ids=[x['id'] for x in batch], embeddings=vectors,
                                   documents=[x['text'] for x in batch],
                                   metadatas=[x['metadata'] for x in batch])

    def remove(self, doc_id: str):
        self.collection.delete(where={'document_id': doc_id})

    def get_doc(self, doc_id: str) -> dict:
        return self.collection.get(where={'document_id': doc_id}, include=['documents','metadatas'])

    def query(self, question: str, collection: str, document_ids: list[str], k: int) -> list[dict]:
        clauses: list[dict] = [{'scope': collection}]
        if document_ids:
            clauses.append({'document_id': {'$in': document_ids}})
        where = {'$and': clauses} if len(clauses)>1 else clauses[0]
        if self.collection.count() == 0:
            return []
        query_vector = self.embedder.embed([question])[0]
        response = self.collection.query(query_embeddings=[query_vector], where=where,
                                         n_results=min(k,self.collection.count()),
                                         include=['metadatas','documents','distances'])
        return [{'id': i, 'text': text, 'metadata': meta, 'distance': float(dist)}
                for i,text,meta,dist in zip(response['ids'][0], response['documents'][0],
                                             response['metadatas'][0], response['distances'][0])]
