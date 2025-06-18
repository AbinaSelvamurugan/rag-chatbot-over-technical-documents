import pytest
from backend.app.core.config import Settings
from backend.app.services.registry import Registry
from backend.app.services.ingestion import Ingestion,validate_url

class FakePersistentIndex:
    """Deterministic contract fake for isolated ingestion tests."""
    def __init__(self):
        self.rows={}
        self.collection=self
    def add(self,rows):
        for row in rows:self.rows[row['id']]=row
    def get_doc(self,doc_id):
        return {'ids':[id for id,row in self.rows.items() if row['metadata']['document_id']==doc_id]}
    def remove(self,doc_id):
        for id in self.get_doc(doc_id)['ids']:self.rows.pop(id)
    def delete(self,ids):
        for id in ids:self.rows.pop(id,None)

@pytest.fixture
def service(tmp_path):
    cfg=Settings(_env_file=None,data_dir=tmp_path,registry_path=tmp_path/'db.sqlite')
    registry=Registry(cfg.registry_path)
    return Ingestion(cfg,registry,FakePersistentIndex()),registry

def test_ingest_duplicate_reindex_delete(service):
    ingest,registry=service
    data=b'# Test\n## Syntax\nshow interfaces terse\n'
    record=ingest.ingest('cli.md',data)
    assert record['status']=='indexed' and record['chunks']>0
    assert ingest.ingest('cli.md',data)['duplicate']
    assert ingest.reindex(record['id'])['id']==record['id']
    assert ingest.index.get_doc(record['id'])['ids']
    ingest.delete(record['id'])
    assert not registry.get(record['id']) and not ingest.index.get_doc(record['id'])['ids']

def test_bad_and_empty(service):
    ingest,registry=service
    with pytest.raises(ValueError):ingest.ingest('bad.gif',b'GIF89')
    with pytest.raises(ValueError):ingest.ingest('empty.md',b'')
    assert any(row['status']=='failed' for row in registry.list())

def test_reject_ssrf(tmp_path):
    cfg=Settings(_env_file=None,allow_url_ingestion=True,allowed_hosts='localhost')
    with pytest.raises(ValueError):validate_url('http://localhost/data',cfg)
    with pytest.raises(ValueError):validate_url('https://127.0.0.1/data',cfg)
    with pytest.raises(ValueError):validate_url('https://localhost:9999/data',cfg)

@pytest.mark.parametrize('value',['../passwd','/etc/passwd','insecure'])
def test_invalid_url(value):
    with pytest.raises(ValueError):validate_url(value,Settings(_env_file=None))


def test_scope_reset_does_not_touch_other_collection(service):
    ingest,reg=service
    data=b'# Sources\nshow configuration\n'
    ingest.ingest('a.md',data,'a')
    ingest.ingest('b.md',data,'b')
    assert ingest.reset_collection('a')==1
    assert len(reg.list('a'))==0
    assert len(reg.list('b'))==1
