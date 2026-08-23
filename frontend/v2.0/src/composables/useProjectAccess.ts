import { computed, readonly, ref } from 'vue'
import { projectApi, type Project, type ProjectMemberList } from '../api'
import { ApiRequestError } from '../api/http'
import { useCurrentUser } from './useCurrentUser'

const projectState = ref<Project | null>(null)
const membersState = ref<ProjectMemberList | null>(null)

const isMember = computed(() => {
  const userId = useCurrentUser().currentUser.value?.id
  return Boolean(userId && membersState.value?.items.some((member) => member.user_id === userId))
})
const readOnly = computed(() =>
  projectState.value?.status === 'ARCHIVED' || !isMember.value,
)

const loadProjectAccess = async (projectId: string) => {
  try {
    const project = await projectApi.detail(projectId)
    const members = await projectApi.listMembers(projectId)
    projectState.value = project
    membersState.value = members
    return true
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 404) {
      projectState.value = null
      membersState.value = null
      return false
    }
    throw error
  }
}

const markCurrentProjectArchived = () => {
  if (projectState.value) projectState.value = { ...projectState.value, status: 'ARCHIVED' }
}

const clearProjectAccess = () => {
  projectState.value = null
  membersState.value = null
}

export const useProjectAccess = () => ({
  project: readonly(projectState),
  members: readonly(membersState),
  isMember,
  readOnly,
  loadProjectAccess,
  markCurrentProjectArchived,
  clearProjectAccess,
})
