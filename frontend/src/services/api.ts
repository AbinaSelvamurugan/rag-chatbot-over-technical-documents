import type {Answer,DocumentRecord,Passage,Scope} from '../types';
export class ApiError extends Error {constructor(public status:number, detail:string){super(detail);this.name='ApiError';}}
export function api(token:string){
  const headers:Record<string,string> = token?{'X-Admin-Token':token}:{};
  async function request<T>(path:string, options:RequestInit={}):Promise<T>{
    const response=await fetch('/api'+path,{...options,headers:{...headers,...options.headers}});
    if(!response.ok){const body=await response.json().catch(()=>({detail:response.statusText}));throw new ApiError(response.status,String(body.detail??response.statusText));}
    if(response.status===204)return undefined as T;
    return response.json() as Promise<T>;
  }
  const json=<T,>(path:string,value:unknown,signal?:AbortSignal)=>request<T>(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value),signal});
  return {
    health:()=>request<{status:string;retrieval_dependencies_installed:boolean;llm_configured:boolean}>('/health'),
    config:()=>request<{embedding_model:string;groq_model:string|null;index_name:string;llm_configured:boolean}>('/config'),
    documents:()=>request<DocumentRecord[]>('/documents'),
    collections:()=>request<{scopes:string[];indexed_documents:number;indexed_chunks:number}>('/collections'),
    upload:(file:File,collection:string)=>{const form=new FormData();form.append('file',file);form.append('collection',collection);return request<DocumentRecord>('/documents/upload',{method:'POST',body:form});},
    ingestUrl:(url:string,collection:string)=>json<DocumentRecord>('/documents/url',{url,collection}),
    original:async(id:string)=>{
      const response=await fetch('/api/documents/'+encodeURIComponent(id)+'/original',{headers});
      if(!response.ok)throw new ApiError(response.status,'Original document unavailable');
      return await response.blob();
    },
    reindex:(id:string)=>request<DocumentRecord>('/documents/'+encodeURIComponent(id)+'/reindex',{method:'POST'}),
    delete:(id:string)=>request<void>('/documents/'+encodeURIComponent(id),{method:'DELETE'}),
    retrieve:(question:string,scope:Scope)=>json<{selected:Passage[];candidates:Passage[];retrieval_ms:number}>('/retrieve',{question,scope}),
    chat:(question:string,scope:Scope,session_id:string|null,signal?:AbortSignal)=>json<Answer>('/chat',{question,scope,session_id},signal),
    clear:(id:string)=>request<void>('/sessions/'+encodeURIComponent(id),{method:'DELETE'}),
    resetCollection:(collection:string,confirmation:string)=>json<{deleted_documents:number}>('/collections/reset',{collection,confirmation}),
    evaluate:()=>json<{questions:number;run_id:string;macro_document_metrics:Record<string,number>}>('/evaluate',{dataset:'local_questions.json',k:5,generate:false})
  };
}
