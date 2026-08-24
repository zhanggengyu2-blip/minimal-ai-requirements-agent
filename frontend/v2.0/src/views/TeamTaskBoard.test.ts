import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it, vi } from 'vitest'
import TeamTaskBoard from './TeamTaskBoard.vue'

const mocks = vi.hoisted(() => ({
  list: vi.fn(),
  listVersions: vi.fn(),
  loadProjectAccess: vi.fn(),
}))

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api')
  return {
    ...actual,
    taskApi: { ...actual.taskApi, list: mocks.list },
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

describe('TeamTaskBoard', () => {
  it('loads unfinished tasks by default and keeps zero-task members visible', async () => {
    mocks.listVersions.mockResolvedValue({ items: [], total: 0 })
    mocks.list.mockResolvedValue({
      total: 1,
      lanes: [
        { assignee_id: 'a'.repeat(32), revision: 1 },
        { assignee_id: 'b'.repeat(32), revision: 1 },
      ],
      items: [{
        id: '1'.repeat(32), project_id: 'p'.repeat(32), assignee_id: 'a'.repeat(32), version_id: null,
        name: '梳理验收标准', description: '', status: 'NOT_STARTED', priority: 'P1', start_date: null,
        due_date: null, sort_order: 1, revision: 1, created_by: 'a'.repeat(32), updated_by: 'a'.repeat(32),
        created_time: '2026-08-24T00:00:00Z', updated_time: '2026-08-24T00:00:00Z',
      }],
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/projects/:projectId/tasks/board', name: 'project-task-board', component: TeamTaskBoard },
        { path: '/projects/:projectId/tasks/gantt', name: 'project-task-gantt', component: { template: '<div />' } },
      ],
    })
    await router.push(`/projects/${'p'.repeat(32)}/tasks/board`)
    await router.isReady()
    const wrapper = mount(TeamTaskBoard, {
      global: {
        plugins: [ElementPlus, router],
        stubs: { TaskDialog: true },
      },
    })
    await flushPromises()

    expect(mocks.list).toHaveBeenCalledWith('p'.repeat(32), {
      keyword: undefined,
      status: 'UNFINISHED',
    })
    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('李四')
    expect(wrapper.text()).toContain('梳理验收标准')
    expect(wrapper.text()).toContain('暂无符合条件的任务')
  })
})
