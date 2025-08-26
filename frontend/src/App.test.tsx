import {beforeEach,afterEach,describe,expect,it,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import App from './App';

const response=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
let failChat=false;
beforeEach(()=>{
  failChat=false;
  Element.prototype.scrollIntoView=vi.fn();
  vi.stubGlobal('fetch',vi.fn(async(input:RequestInfo|URL)=>{
    const url=String(input);
    if(url==='/api/health')return response({status:'degraded'});
    if(url==='/api/config')return response({embedding_model:'test',groq_model:null,index_name:'test',llm_configured:false});
    if(url==='/api/collections')return response({scopes:['default'],indexed_documents:1,indexed_chunks:1});
    if(url==='/api/documents')return response([{id:'document',title:'cli.md',status:'indexed',collection:'default',source_type:'md',chunks:1,extraction_chars:70,updated_at:1,content_hash:'hash'}]);
    if(url==='/api/chat'){
      if(failChat)return response({detail:'Provider unavailable'},503);
      return response({session_id:'test-session',answer:'Use show interfaces terse [S1]',abstained:false,
        claims:[{text:'Use show interfaces terse',source_ids:['S1']}],sources:[{citation_id:'S1',chunk_id:'aaaa',document_id:'document',title:'cli.md',uri:null,section:'CLI',page_number:null,text:'Use show interfaces terse',rank:1,distance:0.12,selected:true}],
        trace:{candidate_count:1,selected_count:1,retrieval_ms:15,llm_ms:25,retrieval_query:'interface',all_candidates:[]},token_usage:{total_tokens:20},latency_ms:40});
    }
    return response({detail:'not found'},404);
  }));
});
afterEach(()=>{cleanup();vi.unstubAllGlobals()});

describe('API-connected interaction contract',()=>{
  it('shows a validated citation from API response and opens its excerpt',async()=>{
    render(<App/>);
    fireEvent.change(screen.getByLabelText('Question'),{target:{value:'Which command is used?'}});
    fireEvent.click(screen.getByRole('button',{name:'Send question'}));
    await waitFor(()=>expect(screen.getByRole('button',{name:'[S1]'})).toBeTruthy());
    fireEvent.click(screen.getByRole('button',{name:'[S1]'}));
    await waitFor(()=>expect(screen.getByText('Distance: 0.1200 (not confidence)')).toBeTruthy());
  });
  it('shows a provider error without a cited answer',async()=>{
    failChat=true;
    render(<App/>);
    fireEvent.change(screen.getByLabelText('Question'),{target:{value:'Which command is used?'}});
    fireEvent.click(screen.getByRole('button',{name:'Send question'}));
    await waitFor(()=>expect(screen.getByRole('alert').textContent).toContain('Provider unavailable'));
    expect(screen.queryByRole('button',{name:'[S1]'})).toBeNull();
  });
});
