import { reactive, toRefs } from 'vue'
import type { TaskStatusFilter } from '../api'
import type { GanttScale } from '../utils/gantt'

const teamState = reactive<{
  projectId: string
  keyword: string
  status: TaskStatusFilter
  scale: GanttScale
}>({ projectId: '', keyword: '', status: 'UNFINISHED', scale: 'week' })

const versionState = reactive<{
  projectId: string
  keyword: string
  status: TaskStatusFilter
  scale: GanttScale
}>({ projectId: '', keyword: '', status: 'ALL', scale: 'week' })

const ensureTeamProject = (projectId: string) => {
  if (teamState.projectId === projectId) return
  Object.assign(teamState, { projectId, keyword: '', status: 'UNFINISHED', scale: 'week' })
}
const resetTeamState = () => Object.assign(teamState, { projectId: '', keyword: '', status: 'UNFINISHED', scale: 'week' })

const ensureVersionProject = (projectId: string) => {
  if (versionState.projectId === projectId) return
  Object.assign(versionState, { projectId, keyword: '', status: 'ALL', scale: 'week' })
}
const resetVersionState = () => Object.assign(versionState, { projectId: '', keyword: '', status: 'ALL', scale: 'week' })

export const useTeamTaskModuleState = () => ({
  ...toRefs(teamState),
  ensureProject: ensureTeamProject,
  reset: resetTeamState,
})

export const useVersionModuleState = () => ({
  ...toRefs(versionState),
  ensureProject: ensureVersionProject,
  reset: resetVersionState,
})
