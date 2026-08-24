import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useTeamTaskModuleState } from '../composables/useTaskModuleState'
import TeamTaskGantt from './TeamTaskGantt.vue'

const projectId = 'p'.repeat(32)
const userId = 'a'.repeat(32)
const mocks = vi.hoisted(() => ({
  listTasks: vi.fn(),
  listVersions: vi.fn(),
  loadProjectAccess: vi.fn(),
}))

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api')
  return {
    ...actual,
    taskApi: { ...actual.taskApi, list: mocks.listTasks },
    versionApi: { ...actual.versionApi, list: mocks.listVersions },
  }
})

vi.mock('../composables/useProjectAccess', async () => {
  const { computed, readonly, ref } = await import('vue')
  const project = ref({ id: 'p'.repeat(32), name: '协作平台', status: 'ACTIVE' })
  const members = ref({
    member_revision: 1,
    items: [
      { user_id: 'a'.repeat(32), name: '张三', department_id: 'd'.repeat(32), department_name: '产品部', role: 'MEMBER', sort_order: 1, task_count: 1, created_time: '2026-08-24T00:00:00Z' },
      { user_id: 'b'.repeat(32), name: '李四', department_id: 'd'.repeat(32), department_name: '研发部', role: 'MEMBER', sort_order: 2, task_count: 0, created_time: '2026-08-24T00:00:00Z' },
    ],
  })
  return {
    useProjectAccess: () => ({
      project: readonly(project),
      members: readonly(members),
      readOnly: computed(() => false),
      loadProjectAccess: mocks.loadProjectAccess,
    }),
  }
})

beforeEach(() => {
  vi.clearAllMocks()
  useTeamTaskModuleState().reset()
})

describe('TeamTaskGantt', () => {
  it('默认加载未完成任务并保留零任务成员', async () => {
    mocks.listVersions.mockResolvedValue({ items: [], total: 0 })
    mocks.listTasks.mockResolvedValue({
      total: 1,
      lanes: [],
      items: [{
        id: '1'.repeat(32), project_id: projectId, assignee_id: userId, version_id: null,
        name: '缺少截止日期', description: '', status: 'NOT_STARTED', priority: 'P1',
        start_date: '2026-08-24', due_date: null, sort_order: 1, revision: 1,
        created_by: userId, updated_by: userId,
        created_time: '2026-08-24T00:00:00Z', updated_time: '2026-08-24T00:00:00Z',
      }],
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/projects/:projectId/tasks/board', name: 'project-task-board', component: { template: '<div />' } },
        { path: '/projects/:projectId/tasks/gantt', name: 'project-task-gantt', component: TeamTaskGantt },
      ],
    })
    await router.push(`/projects/${projectId}/tasks/gantt`)
    await router.isReady()
    const wrapper = mount(RouterView, {
      global: { plugins: [ElementPlus, router], stubs: { TaskDialog: true } },
    })
    await flushPromises()

    expect(mocks.listTasks).toHaveBeenCalledWith(projectId, { keyword: undefined, status: 'UNFINISHED' })
    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('李四')
    expect(wrapper.text()).toContain('缺少截止日期')
    expect(wrapper.findAll('.gantt-task-bar')).toHaveLength(0)
  })
})
