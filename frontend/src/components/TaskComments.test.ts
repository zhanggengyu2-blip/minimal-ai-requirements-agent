import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import ElementPlus from 'element-plus'
import TaskComments from './TaskComments.vue'
import { commentApi } from '../api/taskComments'
vi.mock('../api/taskComments', () => ({ commentApi: { list: vi.fn(), create: vi.fn() } }))
describe('TaskComments', () => {
  it('shows AI authors and sends a reply linked to its parent', async () => {
    vi.mocked(commentApi.list).mockResolvedValue([{ id: 'c', project_id: 'p', task_id: 't', author_id: 'u', actor_type: 'COO', author_name: 'Coo · AI 同事', content: '请调查', parent_id: null, agent_run_id: 'r', created_time: '2026-10-29T00:00:00Z' }])
    vi.mocked(commentApi.create).mockResolvedValue({} as never)
    const w = mount(TaskComments, { props: { projectId: 'p', taskId: 't' }, global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(w.text()).toContain('Coo · AI 同事')
    await w.findAll('button').find(b => b.text() === '回复')!.trigger('click')
    await w.find('textarea').setValue(' 已联系仓库 ')
    await w.findAll('button').find(b => b.text() === '发送留言')!.trigger('click')
    await flushPromises()
    expect(commentApi.create).toHaveBeenCalledWith('p', 't', '已联系仓库', 'c')
    w.unmount()
  })
  it('hides writing controls in archived projects', async () => {
    vi.mocked(commentApi.list).mockResolvedValue([])
    const w = mount(TaskComments, { props: { projectId: 'p', taskId: 't', readOnly: true }, global: { plugins: [ElementPlus] } })
    await flushPromises()
    expect(w.find('textarea').exists()).toBe(false)
    w.unmount()
  })
})
