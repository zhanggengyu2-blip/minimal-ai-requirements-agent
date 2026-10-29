import { http } from './http'
import type { KnowledgeSource } from './knowledge'
export interface CooSession { id: string; title: string; project_id: string|null; created_time: string }
export interface CooAction { id: string; project_id: string; name: string; status: string; arguments: Record<string,unknown>; result: Record<string,unknown>|null; error: string|null }
export interface CooTool { id: string; name: string; status: string; arguments: Record<string,unknown>; result: unknown; error: string|null }
export interface CooRun {id: string; session_id: string|null; project_id: string|null; goal: string; trigger: string; status: string; answer: string|null; error: string|null; error_code: string|null; tools: CooTool[]; actions: CooAction[]; sources: KnowledgeSource[]; created_time: string; finished_time: string|null; token_usage: number|null; model: string|null}
export const cooApi = {
 status:()=>http.get<never,{model_configured:boolean;model:string;mode:string}>('/coo/status'),
 sessions:()=>http.get<never,CooSession[]>('/coo/sessions'),
 create:(project_id:string|null,title='与 Coo 协作')=>http.post<never,CooSession>('/coo/sessions',{project_id,title}),
 history:(id:string)=>http.get<never,{session:CooSession;runs:CooRun[]}>(`/coo/sessions/${id}`),
 send:(id:string,content:string,allow_comments:boolean)=>http.post<never,CooRun>(`/coo/sessions/${id}/messages`,{content,allow_comments},{timeout:310000}),
 run:(id:string)=>http.get<never,CooRun>(`/coo/runs/${id}`),
 decide:(id:string,decision:'APPROVE'|'REJECT')=>http.post<never,CooRun>(`/coo/actions/${id}/decision`,{decision},{timeout:120000}),
}
