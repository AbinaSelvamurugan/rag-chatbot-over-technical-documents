from fastapi.testclient import TestClient
from backend.app.main import app

client=TestClient(app)

def test_health_and_api_contract():
    h=client.get('/api/health')
    assert h.status_code==200
    assert h.json()['status'] in ('ready','degraded')
    bad=client.post('/api/chat',json={'question':''})
    assert bad.status_code==422
    invalid=client.post('/api/retrieve',json={'question':'test','scope':{'collection':'!invalid'}})
    assert invalid.status_code==422

def test_upload_reject_filetype_without_model():
    response=client.post('/api/documents/upload',data={'collection':'default'},files={'file':('bad.exe',b'payload')})
    # Either a rejected file type (400) or an unavailable service (503); never a success response.
    assert response.status_code in (400,503)

def test_missing_document():
    assert client.get('/api/documents/not-found').status_code==404


def test_auth_required_when_configured(monkeypatch):
    from backend.app.main import settings
    cfg=settings()
    monkeypatch.setattr(cfg,'admin_token','some-test-key')
    try:
        assert client.get('/api/documents').status_code==401
        assert client.get('/api/documents',headers={'X-Admin-Token':'some-test-key'}).status_code==200
    finally:
        monkeypatch.setattr(cfg,'admin_token','')


def test_reset_requires_exact_confirmation():
    response=client.post('/api/collections/reset',json={'collection':'default','confirmation':'no thanks'})
    assert response.status_code==400


def test_original_missing():
    assert client.get('/api/documents/no-such-document/original').status_code==404
