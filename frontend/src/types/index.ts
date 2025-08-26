export type Scope = {collection: string; document_ids: string[]};
export type DocumentRecord = {id:string;collection:string;title:string;uri:string|null;source_type:string;status:string;error:string|null;chunks:number;extraction_chars:number;duration_ms:number;updated_at:number;content_hash:string};
export type Passage = {citation_id:string;chunk_id:string;document_id:string;title:string;uri:string|null;section:string|null;page_number:number|null;text:string;rank:number;distance:number|null;selected:boolean};
export type Claim = {text:string;source_ids:string[]};
export type Answer = {session_id:string;answer:string;abstained:boolean;claims:Claim[];sources:Passage[];trace:{candidate_count:number;selected_count:number;retrieval_ms:number;llm_ms:number;retrieval_query:string;all_candidates:Passage[]};token_usage:Record<string,number>;latency_ms:number};
export type Message = {role:'user'|'assistant';text:string;answer?:Answer};
