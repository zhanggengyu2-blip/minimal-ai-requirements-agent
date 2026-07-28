import { http } from './http'
import type { components, operations } from './generated'

export type Project = components['schemas']['ProjectRead']
export type ProjectCreate = components['schemas']['ProjectCreate']
export type Requirement = components['schemas']['RequirementRead']
export type RequirementCreate = components['schemas']['RequirementCreate']
export type BatchAnalyzeAccepted = components['schemas']['BatchAnalyzeAccepted']
export type ProjectStatus = components['schemas']['ProjectStatus']
export type RequirementPriority = components['schemas']['RequirementPriority']
export type RequirementType = components['schemas']['RequirementType']
export type AnalysisStatus = components['schemas']['AnalysisStatus']
export type Department = components['schemas']['DepartmentRead']
export type DepartmentCreate = components['schemas']['DepartmentCreate']
export type DepartmentUpdate = components['schemas']['DepartmentUpdate']
export type DepartmentStatus = components['schemas']['DepartmentStatus']
export type Invitation = components['schemas']['InvitationRead']
export type InvitationCreate = components['schemas']['InvitationCreate']
export type InvitationStatus = components['schemas']['InvitationStatus']
export type ProjectListParams = NonNullable<operations['list_projects_api_v1_projects_get']['parameters']['query']>
export type RequirementListParams = NonNullable<operations['list_requirements_api_v1_requirements_get']['parameters']['query']>
export type DepartmentListParams = NonNullable<operations['list_departments_api_v1_departments_get']['parameters']['query']>
export type InvitationListParams = NonNullable<operations['list_invitations_api_v1_invitations_get']['parameters']['query']>

export interface PageData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export const projectApi = {
  list: (params: ProjectListParams) =>
    http.get<never, PageData<Project>>('/projects', { params }),
  create: (data: ProjectCreate) =>
    http.post<never, Project>('/projects', data),
}

export const requirementApi = {
  list: (params: RequirementListParams) =>
    http.get<never, PageData<Requirement>>('/requirements', { params }),
  create: (data: RequirementCreate) =>
    http.post<never, Requirement>('/requirements', data),
  detail: (requirementId: string) =>
    http.get<never, Requirement>(`/requirements/${requirementId}`),
  batchAnalyze: (requirementIds: string[]) =>
    http.post<never, BatchAnalyzeAccepted>('/requirements/batch-analyze', {
      requirement_ids: requirementIds,
    }),
}

export const departmentApi = {
  list: (params: DepartmentListParams) =>
    http.get<never, PageData<Department>>('/departments', { params }),
  create: (data: DepartmentCreate) =>
    http.post<never, Department>('/departments', data),
  update: (departmentId: string, data: DepartmentUpdate) =>
    http.patch<never, Department>(`/departments/${departmentId}`, data),
}

export const invitationApi = {
  list: (params: InvitationListParams) =>
    http.get<never, PageData<Invitation>>('/invitations', { params }),
  create: (data: InvitationCreate) =>
    http.post<never, Invitation>('/invitations', data),
  disable: (invitationId: string) =>
    http.post<never, Invitation>(`/invitations/${invitationId}/disable`),
}
