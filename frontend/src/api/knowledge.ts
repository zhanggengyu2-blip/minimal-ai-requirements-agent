import { http } from './http'
export interface KnowledgeCategory {id: string; name: string; scope: 'ENTERPRISE'|'PROJECT'; project_id: string|null; department_id: string|null}
export interface ChunkSettings {separator: string; target_chars: number; overlap_chars: number}
export interface KnowledgeVersion {id: string; version: number; status: string; error: string|null; content?: string; settings: ChunkSettings; effective_from: string|null; effective_until: string|null}
export interface KnowledgeDocument {id: string; title: string; category_id: string; revision: number; enabled: boolean; state: string; active_version_id: string|null; versions: KnowledgeVersion[]}
export interface KnowledgeSave {title: string; category_id: string; content: string; expected_revision: number; settings: ChunkSettings; effective_from: string|null; effective_until: string|null}
export interface KnowledgeSource {id: string; content: string; document_id: string; document_title: string; version_id: string; version: number; score: number}
export interface KnowledgeSearch {results: KnowledgeSource[]; warnings: string[]; score_kind: string; rerank_applied: boolean}
export const knowledgeApi = {
 categories: () => http.get<never,KnowledgeCategory[]>('/knowledge/categories'),
 createCategory: (body: object) => http.post<never,KnowledgeCategory>('/knowledge/categories', body),
 list: () => http.get<never,KnowledgeDocument[]>('/knowledge/documents'),
 detail: (id: string) => http.get<never,KnowledgeDocument>(`/knowledge/documents/${id}`),
 save: (id: string|null, body: KnowledgeSave) => id ? http.put<never,KnowledgeDocument>(`/knowledge/documents/${id}`,body) : http.post<never,KnowledgeDocument>('/knowledge/documents',body),
 publish: (id: string, expected_revision: number) => http.post<never,KnowledgeDocument>(`/knowledge/documents/${id}/publish`,{expected_revision}, { timeout: 180000 }),
 enable: (doc: KnowledgeDocument) => http.patch<never,KnowledgeDocument>(`/knowledge/documents/${doc.id}/enabled`,{expected_revision:doc.revision,enabled:!doc.enabled}),
 restore: (doc: KnowledgeDocument) => http.post<never,KnowledgeDocument>(`/knowledge/documents/${doc.id}/restore`,{expected_revision:doc.revision}),
 preview: (content: string, settings: ChunkSettings) => http.post<never,{chunks:string[]}>('/knowledge/preview',{content,settings}),
 upload: (file: File) => {const body=new FormData();body.append('file',file);return http.post<never,{content:string}>('/knowledge/upload',body)},
 search: (query: string, project_id: string|null) => http.post<never,KnowledgeSearch>('/knowledge/search',{query,project_id}, { timeout: 90000 }),
}
