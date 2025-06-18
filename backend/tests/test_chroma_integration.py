"""Contract tests for the persistent Chroma store."""
import pytest
pytest.importorskip('chromadb')
from backend.app.services.vectorstore import VectorStore,IndexErrorState

class ThreeDimensionalEmbedder:
    model_name='test-three-dimension'
    dimension=3
    batch_size=4
    def embed(self,texts):
        return [[1.0,0.0,0.0] if 'interface' in t.lower() else [0.0,1.0,0.0] for t in texts]

def test_persistence_scope_and_deletion(tmp_path):
    store=VectorStore(tmp_path/'db','testcollection',ThreeDimensionalEmbedder())
    store.add([
      {'id':'a'*24,'text':'interface mode','metadata':{'document_id':'a','scope':'a','source_title':'a.md'}},
      {'id':'b'*24,'text':'backup process','metadata':{'document_id':'b','scope':'b','source_title':'b.md'}}
    ])
    reopened=VectorStore(tmp_path/'db','testcollection',ThreeDimensionalEmbedder())
    found=reopened.query('interface status','a',[],3)
    assert len(found)==1 and found[0]['id']=='a'*24
    assert reopened.query('interface status','b',[],3)[0]['id']=='b'*24
    reopened.remove('a')
    assert not store.get_doc('a')['ids']
    assert store.get_doc('b')['ids']

def test_model_signature_prevents_mixing(tmp_path):
    VectorStore(tmp_path/'db','testcollection',ThreeDimensionalEmbedder())
    different=ThreeDimensionalEmbedder()
    different.model_name='incompatible-model'
    with pytest.raises(IndexErrorState):
        VectorStore(tmp_path/'db','testcollection',different)
