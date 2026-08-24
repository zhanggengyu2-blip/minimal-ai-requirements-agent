import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { afterEach, describe, expect, it } from 'vitest'
import { ApiRequestError } from '../api/http'
import TaskDialog from './TaskDialog.vue'

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
})
