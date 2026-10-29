import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from '../api/http'
import TaskDialog from './TaskDialog.vue'
vi.mock('../api/taskComments', () => ({ commentApi: { list: vi.fn().mockResolvedValue([]), create: vi.fn() } }))

const member = {
  user_id: 'a'.repeat(32),
  name: '张三',
  department_id: 'd'.repeat(32),
  department_name: '产品部',
  role: 'MEMBER' as const,
  sort_order: 1,
  task_count: 0,
  created_time: '2026-08-24T00:00:00Z',
}

afterEach(() => {
  document.body.innerHTML = ''
})

describe('TaskDialog', () => {
  it('offers real versions in the shared task form', async () => {
    const wrapper = mount(TaskDialog, {
      props: {
        modelValue: false,
        projectId: 'p'.repeat(32),
        members: [member],
        initialVersionId: 'v'.repeat(32),
        versions: [{
          id: 'v'.repeat(32), project_id: 'p'.repeat(32), name: 'V3.0 团队任务与版本排期',
          start_date: '2026-08-01', end_date: '2026-08-31', status: 'IN_PROGRESS', revision: 1,
          task_count: 0, unfinished_task_count: 0, created_by: member.user_id, updated_by: member.user_id,
          created_time: '2026-08-24T00:00:00Z', updated_time: '2026-08-24T00:00:00Z',
        }],
      },
      attachTo: document.body,
      global: { plugins: [ElementPlus] },
    })
    await wrapper.setProps({ modelValue: true })
    await flushPromises()

    expect(document.body.textContent).toContain('V3.0 团队任务与版本排期')
    expect(document.body.textContent).not.toContain('T7 接入版本选择')
  })

  it('shows task capacity failures with the confirmed create wording', async () => {
    const wrapper = mount(TaskDialog, {
      props: {
        modelValue: false,
        projectId: 'p'.repeat(32),
        members: [member],
      },
      attachTo: document.body,
      global: { plugins: [ElementPlus] },
    })
    await wrapper.setProps({ modelValue: true })
    const vm = wrapper.vm as unknown as {
      handleFailure: (error: unknown, action: 'create' | 'save' | 'delete') => void
    }
    vm.handleFailure(
      new ApiRequestError('成员任务已满', 409, 'TASK_ASSIGNEE_LIMIT_REACHED'),
      'create',
    )
    await flushPromises()

    expect(document.body.textContent).toContain('创建失败：该成员已达到任务上限')
  })

  it('turns an archived task dialog into a view-only surface', async () => {
    const wrapper = mount(TaskDialog, {
      props: {
        modelValue: false,
        projectId: 'p'.repeat(32),
        members: [member],
        readOnly: true,
      },
      attachTo: document.body,
      global: { plugins: [ElementPlus] },
    })
    await wrapper.setProps({ modelValue: true })
    await flushPromises()

    expect(document.body.textContent).toContain('查看任务')
    expect(document.body.textContent).toContain('仅支持查看')
    expect(document.body.textContent).not.toContain('创建任务')
  })

  it('uses a generic permanent-delete confirmation without repeating the task name', async () => {
    const taskName = '不应出现在删除确认中的任务名'
    const wrapper = mount(TaskDialog, {
      props: {
        modelValue: false,
        projectId: 'p'.repeat(32),
        members: [member],
        task: {
          id: 't'.repeat(32), project_id: 'p'.repeat(32), assignee_id: member.user_id, version_id: null,
          name: taskName, description: '', status: 'NOT_STARTED', priority: 'P1', start_date: null,
          due_date: null, sort_order: 1, revision: 1, created_by: member.user_id, updated_by: member.user_id,
          created_time: '2026-08-24T00:00:00Z', updated_time: '2026-08-24T00:00:00Z',
        },
      },
      attachTo: document.body,
      global: { plugins: [ElementPlus] },
    })
    await wrapper.setProps({ modelValue: true })
    await flushPromises()
    const deleteButton = wrapper.findAll('button').find((button) => button.text().includes('删除任务'))
    await deleteButton?.trigger('click')
    await flushPromises()

    const confirmation = document.querySelector('.task-delete-dialog')?.textContent || ''
    expect(confirmation).toContain('删除后任务将无法恢复')
    expect(confirmation).not.toContain(taskName)
  })
})
