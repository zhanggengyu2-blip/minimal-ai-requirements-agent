import { http } from './http'
export interface TaskComment {
  id: string; project_id: string; task_id: string; author_id: string; author_name: string
  actor_type: 'HUMAN' | 'COO'; parent_id: string | null; content: string; agent_run_id: string | null; created_time: string
}
export const commentApi = {
  list: (project: string, task: string, before?: string) => http.get<never, TaskComment[]>(`/projects/${project}/tasks/${task}/comments`, { params: { before } }),
  create: (project: string, task: string, content: string, parent_id: string | null) => http.post<never, TaskComment>(`/projects/${project}/tasks/${task}/comments`, { content, parent_id }),
}
