import { http } from './http'
import type { components, operations } from './generated'

export type Project = components['schemas']['ProjectRead']
export type ProjectCreate = components['schemas']['ProjectCreate']
export type ProjectUpdate = components['schemas']['ProjectUpdate']
export type ProjectMember = components['schemas']['ProjectMemberRead']
export type ProjectMemberList = components['schemas']['ProjectMemberList']
export type ProjectMembersUpdate = components['schemas']['ProjectMembersUpdate']
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
export type Invitation = components['schemas']['InvitationRead']
export type InvitationCreate = components['schemas']['InvitationCreate']
export type InvitationStatus = components['schemas']['InvitationStatus']
export type InterviewSession = components['schemas']['InterviewSessionRead']
export type InterviewMessage = components['schemas']['InterviewMessageRead']
export type CurrentUser = components['schemas']['CurrentUserRead']
export type AuthSession = components['schemas']['AuthSessionRead']
export type LoginRequest = components['schemas']['SessionCreateRequest']
export type RegistrationRequest = components['schemas']['RegistrationRequest']
export type LoginDepartment = components['schemas']['DepartmentOption']
export type User = components['schemas']['UserRead']
export type ProjectListParams = NonNullable<operations['list_projects_api_v1_projects_get']['parameters']['query']>
export type RequirementListParams = NonNullable<operations['list_requirements_api_v1_requirements_get']['parameters']['query']>
export type DepartmentListParams = NonNullable<operations['list_departments_api_v1_departments_get']['parameters']['query']>
export type InvitationListParams = NonNullable<operations['list_invitations_api_v1_invitations_get']['parameters']['query']>
export type UserListParams = NonNullable<operations['list_users_api_v1_users_get']['parameters']['query']>

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
  detail: (projectId: string) =>
    http.get<never, Project>(`/projects/${projectId}`, { skipGlobalError: true }),
  update: (projectId: string, data: ProjectUpdate) =>
    http.patch<never, Project>(`/projects/${projectId}`, data),
  listMembers: (projectId: string) =>
    http.get<never, ProjectMemberList>(`/projects/${projectId}/members`),
  saveMembers: (projectId: string, data: ProjectMembersUpdate) =>
    http.put<never, ProjectMemberList>(`/projects/${projectId}/members`, data),
}

export const authApi = {
  departments: () =>
    http.get<never, LoginDepartment[]>('/auth/departments', { skipAuthRedirect: true }),
  register: (data: RegistrationRequest) =>
    http.post<never, AuthSession>('/auth/registrations', data, {
      skipAuthRedirect: true,
      skipGlobalError: true,
    }),
  login: (data: LoginRequest) =>
    http.post<never, AuthSession>('/auth/sessions', data, {
      skipAuthRedirect: true,
      skipGlobalError: true,
    }),
  me: () =>
    http.get<never, AuthSession>('/auth/me', {
      skipGlobalError: true,
      skipAuthRedirect: true,
    }),
  logout: () =>
    http.delete<never, { revoked: boolean }>('/auth/session'),
}

export const userApi = {
  list: (params: UserListParams = {}) =>
    http.get<never, PageData<User>>('/users', { params }),
  listAll: async () => {
    const firstPage = await http.get<never, PageData<User>>('/users', {
      params: { page: 1, page_size: 100 },
    })
    const pageCount = Math.ceil(firstPage.total / firstPage.page_size)
    if (pageCount <= 1) return firstPage.items
    const remainingPages = await Promise.all(
      Array.from({ length: pageCount - 1 }, (_, index) =>
        http.get<never, PageData<User>>('/users', {
          params: { page: index + 2, page_size: 100 },
        }),
      ),
    )
    return [firstPage, ...remainingPages].flatMap((page) => page.items)
  },
}

export const requirementApi = {
  list: (params: RequirementListParams) =>
    http.get<never, PageData<Requirement>>('/requirements', { params }),
  create: (data: RequirementCreate) =>
    http.post<never, Requirement>('/requirements', data),
  detail: (requirementId: string) =>
    http.get<never, Requirement>(`/requirements/${requirementId}`),
  interview: (requirementId: string) =>
    http.get<never, InterviewSession>(`/requirements/${requirementId}/interview`),
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
  delete: (departmentId: string) =>
    http.delete<never, null>(`/departments/${departmentId}`),
}

export const invitationApi = {
  list: (params: InvitationListParams) =>
    http.get<never, PageData<Invitation>>('/invitations', { params }),
  create: (data: InvitationCreate) =>
    http.post<never, Invitation>('/invitations', data),
  disable: (invitationId: string) =>
    http.post<never, Invitation>(`/invitations/${invitationId}/disable`),
}
