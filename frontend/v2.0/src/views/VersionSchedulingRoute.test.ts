import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import VersionSchedulingRoute from './VersionSchedulingRoute.vue'

const projectId = 'p'.repeat(32)
const versionId = 'v'.repeat(32)
const userId = 'a'.repeat(32)
const mocks = vi.hoisted(() => ({
  listVersions: vi.fn(), detailVersion: vi.fn(), completionImpact: vi.fn(), updateVersion: vi.fn(), deleteVersion: vi.fn(),
  listTasks: vi.fn(), loadProjectAccess: vi.fn(),
}))

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api')
  return {
    ...actual,
    versionApi: {
      ...actual.versionApi,
      list: mocks.listVersions,
      detail: mocks.detailVersion,
      completionImpact: mocks.completionImpact,
      update: mocks.updateVersion,
      delete: mocks.deleteVersion,
    },
    taskApi: { ...actual.taskApi, list: mocks.listTasks },
  }
})

vi.mock('../composables/useProjectAccess', async () => {
  const { computed, readonly, ref } = await import('vue')
  const project = ref({ id: 'p'.repeat(32), name: '协作平台', status: 'ACTIVE' })
  const members = ref({
    member_revision: 1,
    items: [{ user_id: 'a'.repeat(32), name: '张三', department_id: 'd'.repeat(32), department_name: '产品部', role: 'MEMBER', sort_order: 1, task_count: 0, created_time: '2026-08-24T00:00:00Z' }],
  })
  return { useProjectAccess: () => ({ project: readonly(project), members: readonly(members), readOnly: computed(() => false), loadProjectAccess: mocks.loadProjectAccess }) }
})

const summary = {
  id: versionId, project_id: projectId, name: 'V3.0', start_date: '2026-08-01', end_date: '2026-08-31',
  status: 'IN_PROGRESS' as const, revision: 2, task_count: 0, unfinished_task_count: 0,
  created_by: userId, updated_by: userId, created_time: '2026-08-24T00:00:00Z', updated_time: '2026-08-24T00:00:00Z',
}
const detail = {
  ...summary,
  participants: [{ user_id: userId, name: '张三', department_id: 'd'.repeat(32), department_name: '产品部', role: 'MEMBER' as const, sort_order: 1, task_count: 0, created_time: '2026-08-24T00:00:00Z' }],
}
const makeRouter = () => createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/projects/:projectId/versions', name: 'project-versions', component: VersionSchedulingRoute },
    { path: '/projects/:projectId/versions/:versionId/list', name: 'project-version-list', component: VersionSchedulingRoute },
    { path: '/projects/:projectId/versions/:versionId/gantt', name: 'project-version-gantt', component: { template: '<div />' } },
  ],
})

beforeEach(() => {
  vi.clearAllMocks()
  mocks.listTasks.mockResolvedValue({ items: [], total: 0, lanes: [] })
})

describe('VersionSchedulingRoute', () => {
  it('shows the no-version state without auto-creating data', async () => {
    mocks.listVersions.mockResolvedValue({ items: [], total: 0 })
    const router = makeRouter()
    await router.push(`/projects/${projectId}/versions`)
    await router.isReady()
    const wrapper = mount(VersionSchedulingRoute, { global: { plugins: [ElementPlus, router], stubs: { VersionDialog: true, TaskDialog: true } } })
    await flushPromises()

    expect(wrapper.text()).toContain('还没有版本排期')
    expect(wrapper.text()).toContain('创建第一个版本')
    expect(mocks.detailVersion).not.toHaveBeenCalled()
  })

  it('keeps zero-task participants visible and uses the ALL filter by default', async () => {
    mocks.listVersions.mockResolvedValue({ items: [summary], total: 1 })
    mocks.detailVersion.mockResolvedValue(detail)
    const router = makeRouter()
    await router.push(`/projects/${projectId}/versions/${versionId}/list`)
    await router.isReady()
    const wrapper = mount(VersionSchedulingRoute, { global: { plugins: [ElementPlus, router], stubs: { VersionDialog: true, TaskDialog: true } } })
    await flushPromises()

    expect(mocks.listTasks).toHaveBeenCalledWith(projectId, { version_id: versionId, keyword: undefined, status: 'ALL' })
    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('产品部')
    expect(wrapper.text()).toContain('0 个任务')
    expect(wrapper.text()).toContain('添加任务')
  })

  it('shows unfinished impact before completing a version', async () => {
    mocks.listVersions.mockResolvedValue({ items: [summary], total: 1 })
    mocks.detailVersion.mockResolvedValue({ ...detail, task_count: 3, unfinished_task_count: 2 })
    mocks.completionImpact.mockResolvedValue({ version_id: versionId, task_count: 3, unfinished_task_count: 2 })
    const router = makeRouter()
    await router.push(`/projects/${projectId}/versions/${versionId}/list`)
    await router.isReady()
    const wrapper = mount(VersionSchedulingRoute, { attachTo: document.body, global: { plugins: [ElementPlus, router], stubs: { VersionDialog: true, TaskDialog: true } } })
    await flushPromises()
    const vm = wrapper.vm as unknown as { requestStatusChange: (status: 'COMPLETED') => Promise<void> }
    await vm.requestStatusChange('COMPLETED')
    await flushPromises()

    expect(document.body.textContent).toContain('共有 3 条任务')
    expect(document.body.textContent).toContain('2 条尚未完成')
    expect(document.body.textContent).toContain('不会改变任何任务状态')
    wrapper.unmount()
    document.body.innerHTML = ''
  })

  it('returns to the no-version route after deleting the final version', async () => {
    mocks.listVersions
      .mockResolvedValueOnce({ items: [summary], total: 1 })
      .mockResolvedValue({ items: [], total: 0 })
    mocks.detailVersion.mockResolvedValue({ ...detail, task_count: 2 })
    mocks.deleteVersion.mockResolvedValue({ unlinked_task_count: 2, next_version_id: null })
    const router = makeRouter()
    await router.push(`/projects/${projectId}/versions/${versionId}/list`)
    await router.isReady()
    const wrapper = mount(VersionSchedulingRoute, { global: { plugins: [ElementPlus, router], stubs: { VersionDialog: true, TaskDialog: true } } })
    await flushPromises()
    const vm = wrapper.vm as unknown as { confirmDelete: () => Promise<void> }
    await vm.confirmDelete()
    await flushPromises()

    expect(mocks.deleteVersion).toHaveBeenCalledWith(projectId, versionId, 2)
    expect(router.currentRoute.value.name).toBe('project-versions')
    expect(wrapper.text()).toContain('还没有版本排期')
  })
})
