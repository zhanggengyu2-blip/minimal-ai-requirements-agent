import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { describe, expect, it } from 'vitest'
import type { Task } from '../api'
import GanttShell from './GanttShell.vue'

const projectId = 'p'.repeat(32)
const assigneeId = 'a'.repeat(32)
const baseTask = (overrides: Partial<Task>): Task => ({
  id: '1'.repeat(32),
  project_id: projectId,
  assignee_id: assigneeId,
  version_id: null,
  name: '完整日期任务',
  description: '',
  status: 'IN_PROGRESS',
  priority: 'P1',
  start_date: '2026-08-20',
  due_date: '2026-08-22',
  sort_order: 1,
  revision: 1,
  created_by: assigneeId,
  updated_by: assigneeId,
  created_time: '2026-08-20T00:00:00Z',
  updated_time: '2026-08-20T00:00:00Z',
  ...overrides,
})

describe('GanttShell', () => {
  it('保留零任务成员，且仅为日期完整的任务绘制任务条', async () => {
    const complete = baseTask({})
    const incomplete = baseTask({
      id: '2'.repeat(32),
      name: '缺少截止日期',
      due_date: null,
      sort_order: 2,
    })
    const wrapper = mount(GanttShell, {
      props: {
        members: [
          { user_id: assigneeId, name: '张三', department_name: '产品部' },
          { user_id: 'b'.repeat(32), name: '李四', department_name: '研发部' },
        ],
        tasks: [complete, incomplete],
        scale: 'week',
      },
      global: { plugins: [ElementPlus] },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('李四')
    expect(wrapper.text()).toContain('0 个任务')
    expect(wrapper.text()).toContain('缺少截止日期')
    expect(wrapper.findAll('.gantt-task-bar')).toHaveLength(1)
    expect(wrapper.find('.gantt-task-bar').text()).toBe('3 天')
    expect(wrapper.find('[draggable="true"]').exists()).toBe(false)

    await wrapper.find('.gantt-task-name').trigger('click')
    await wrapper.find('.gantt-task-bar').trigger('click')
    expect(wrapper.emitted('open')).toEqual([[complete], [complete]])
  })

  it('切换刻度并支持今天与窗口移动控件', async () => {
    const wrapper = mount(GanttShell, {
      props: { members: [], tasks: [], scale: 'week' },
      global: { plugins: [ElementPlus] },
    })
    await flushPromises()

    await wrapper.findAll('.gantt-scale-switch button')[0].trigger('click')
    expect(wrapper.emitted('update:scale')).toEqual([['day']])
    expect(wrapper.find('.gantt-today-button').text()).toBe('今天')
    expect(wrapper.find('[aria-label="向前移动一个窗口"]').exists()).toBe(true)
    expect(wrapper.find('[aria-label="向后移动一个窗口"]').exists()).toBe(true)
  })
})
