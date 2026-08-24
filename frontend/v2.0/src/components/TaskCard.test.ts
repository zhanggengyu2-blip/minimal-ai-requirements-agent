import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { describe, expect, it } from 'vitest'
import type { Task } from '../api'
import TaskCard from './TaskCard.vue'

const task: Task = {
  id: '1'.repeat(32),
  project_id: '2'.repeat(32),
  assignee_id: '3'.repeat(32),
  version_id: null,
  name: '完成任务面板联调',
  description: '验证任务状态和优先级展示。',
  status: 'IN_PROGRESS',
  priority: 'P0',
  start_date: '2026-08-24',
  due_date: '2026-08-26',
  sort_order: 1,
  revision: 1,
  created_by: '3'.repeat(32),
  updated_by: '3'.repeat(32),
  created_time: '2026-08-24T00:00:00Z',
  updated_time: '2026-08-24T00:00:00Z',
}

describe('TaskCard', () => {
  it('renders task state, priority, dates and the drag handle', () => {
    const wrapper = mount(TaskCard, {
      props: { task },
      global: { plugins: [ElementPlus] },
    })

    expect(wrapper.text()).toContain('完成任务面板联调')
    expect(wrapper.text()).toContain('进行中')
    expect(wrapper.text()).toContain('P0 · 重要且紧急')
    expect(wrapper.text()).toContain('2026-08-24 至 2026-08-26')
    expect(wrapper.find('[aria-label="拖动调整任务顺序"]').exists()).toBe(true)
  })

  it('removes the drag handle in read-only mode', () => {
    const wrapper = mount(TaskCard, {
      props: { task, readOnly: true },
      global: { plugins: [ElementPlus] },
    })
    expect(wrapper.find('[aria-label="拖动调整任务顺序"]').exists()).toBe(false)
  })
})
