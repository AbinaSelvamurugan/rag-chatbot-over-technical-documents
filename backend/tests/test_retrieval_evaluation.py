from backend.app.services.retrieval import Retriever,lexical_score
from backend.app.services.evaluation import retrieval_metrics,evaluate
from backend.app.core.config import Settings
from backend.app.schemas import Scope

class LocalVector:
    def query(self,question,collection,document_ids,k):
        docs=[('aa','junos_cli_field_notes.md','configure mode and show interfaces terse for Junos interface status'),
              ('bb','network_troubleshooting.md','inspect physical cables and interfaces'),
              ('cc','system_operations.txt','record service health and errors')]
        return [{'id':id,'text':text,'distance':0.1+(i*.1),
                 'metadata':{'scope':'default','document_id':id,'source_title':title}}
                for i,(id,title,text) in enumerate(docs) if not document_ids or id in document_ids][:k]

def test_metrics_real_formula():
    m=retrieval_metrics(['a','b','c'],{'b','c'},3)
    assert m['precision_at_k']==2/3 and m['recall_at_k']==1
    assert m['mrr']==0.5 and m['hit_rate_at_k']==1
    assert 0<m['ndcg_at_k']<1

def test_filter_and_threshold(tmp_path):
    config=Settings(_env_file=None,data_dir=tmp_path,distance_threshold=.21)
    retriever=Retriever(config,LocalVector())
    result=retriever.retrieve('show interfaces terse',Scope(document_ids=['aa']))
    assert len(result.selected)==1
    assert result.selected[0].title=='junos_cli_field_notes.md'
    assert result.candidates[0].chunk_id=='aa'
    assert lexical_score('interfaces terse','show interfaces terse')==1

def test_no_query():
    retriever=Retriever(Settings(_env_file=None),LocalVector())
    try:retriever.retrieve(' ',Scope());assert False
    except ValueError:pass

def test_actual_evaluation_saved(tmp_path):
    import json
    fixture=tmp_path/'fixture.json'
    fixture.write_text(json.dumps({'questions':[{'id':'x','question':'interfaces','category':'cli','relevant_documents':['junos_cli_field_notes.md']},
                                            {'id':'y','question':'unknown','category':'unanswerable','relevant_documents':[]}]}))
    run=evaluate(fixture,tmp_path/'results',Retriever(Settings(_env_file=None),LocalVector()),None,k=2)
    assert run['questions']==2 and run['macro_document_metrics']['hit_rate_at_k']==1
    assert (tmp_path/'results'/f"{run['run_id']}.json").exists()
