"""Local smoke testing without Groq credentials; checks ingestion and vector query."""
from pathlib import Path
from backend.app.main import services
from backend.app.schemas import Scope

def main():
    ingestion,retriever,_,index=services()
    file=Path('data/sample_documents/junos_cli_field_notes.md')
    ingestion.ingest(file.name,file.read_bytes())
    found=retriever.retrieve('Which command lists interface state?',Scope())
    assert found.selected, 'Smoke test failed: no matching passages'
    assert all(index.get_doc(s.document_id)['ids'] for s in found.selected)
    print('PASS: persisted vector query returned traceable chunks:',len(found.selected))

if __name__=='__main__':main()
