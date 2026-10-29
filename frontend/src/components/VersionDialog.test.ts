import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { afterEach, describe, expect, it } from 'vitest'
import { ApiRequestError } from '../api/http'
import VersionDialog from './VersionDialog.vue'

const member = {
  user_id: 'a'.repeat(32), name: '张三', department_id: 'd'.repeat(32), department_name: '产品部',
  role: 'MEMBER' as const, sort_order: 1, task_count: 1, created_time: '2026-08-24T00:00:00Z',
}
const version = {
  id: 'v'.repeat(32), project_id: 'p'.repeat(32), name: 'V3.0', start_date: '2026-08-01', end_date: '2026-08-31',
  status: 'IN_PROGRESS' as const, revision: 2, task_count: 1, unfinished_task_count: 1,
  created_by: member.user_id, updated_by: member.user_id,
  created_time: '2026-08-24T00:00:00Z', updated_time: '2026-08-24T00:00:00Z',
  participants: [{ ...member, task_count: 1 }],
}

afterEach(() => { document.body.innerHTML = '' })

describe('VersionDialog', () => {
  it('shows departments and protects participants who still own version tasks', async () => {
    const wrapper = mount(VersionDialog, {
      props: { modelValue: false, projectId: version.project_id, members: [member], version },
      attachTo: document.body,
      global: { plugins: [ElementPlus] },
    })
    await wrapper.setProps({ modelValue: true })
    await flushPromises()

    expect(document.body.textContent).toContain('产品部')
    expect(document.body.textContent).toContain('已选人员（1）')
    expect(document.body.textContent).toContain('移除')

    const vm = wrapper.vm as unknown as { handleFailure: (error: unknown) => void }
    vm.handleFailure(new ApiRequestError('冲突', 409, 'VERSION_REVISION_CONFLICT'))
    await flushPromises()
    expect(document.body.textContent).toContain('版本已被其他人修改')
  })
})
