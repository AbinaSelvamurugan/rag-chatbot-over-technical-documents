from backend.app.services.registry import Registry

def test_sessions_scoped_and_cleared(tmp_path):
    r=Registry(tmp_path/'registry.sqlite')
    sid,history=r.session(None,{'collection':'a','document_ids':[]},12)
    assert not history
    r.append(sid,'What is a CLI?','An interface')
    sid2,history=r.session(sid,{'collection':'a','document_ids':[]},12)
    assert sid==sid2 and len(history)==2
    sid3,history=r.session(sid,{'collection':'b','document_ids':[]},12)
    assert sid3!=sid and not history
    r.clear_session(sid3)
    assert r.session(sid3,{'collection':'b','document_ids':[]},12)[0]!=sid3
