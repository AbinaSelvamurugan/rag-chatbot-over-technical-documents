"""Contract tests for LangChain prompt construction with a mocked Groq SDK boundary."""
from types import SimpleNamespace
import pytest
pytest.importorskip('langchain_core')
from backend.app.core.config import Settings
from backend.app.schemas import Passage
from backend.app.services.generation import Generator,ProviderError
from backend.app.services.citations import CitationError

passage=Passage(citation_id='S1',chunk_id='a'*24,document_id='a',title='cli.md',rank=1,
    text='Use show interfaces terse for interface state inspection.')

class Completions:
    def __init__(self,content,fail=False):self.content,self.fail=content,fail
    def create(self,**kwargs):
        assert kwargs['model']=='test-account-model'
        assert kwargs['messages'][0]['role']=='system'
        assert '<source id="S1">' in kwargs['messages'][1]['content']
        if self.fail:raise TimeoutError('Provider timeout')
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content=self.content))],
          usage=SimpleNamespace(prompt_tokens=20,completion_tokens=10,total_tokens=30))

@pytest.mark.parametrize('response,expected',[
    ('{"claims":[{"text":"Use show interfaces terse for interface state inspection.","source_ids":["S1"]}]}',None),
    ('{"claims":[{"text":"Use show interfaces terse for interface state inspection.","source_ids":["S2"]}]}',CitationError)
])
def test_generation_verification(response,expected):
    gen=Generator(Settings(_env_file=None,groq_api_key='test',groq_model='test-account-model'))
    gen._client=lambda:SimpleNamespace(chat=SimpleNamespace(completions=Completions(response)))
    if expected:
        with pytest.raises(expected):gen.generate('What command?', [passage], [])
    else:
        text,claims,tokens,ms,abstained=gen.generate('What command?',[passage],[])
        assert '[S1]' in text and not abstained and tokens['total_tokens']==30


def test_retryable_provider_failure_propagates():
    gen=Generator(Settings(_env_file=None,groq_api_key='test',groq_model='test-account-model'))
    gen._client=lambda:SimpleNamespace(chat=SimpleNamespace(completions=Completions('',fail=True)))
    with pytest.raises(ProviderError):gen.generate('What command?',[passage],[])
