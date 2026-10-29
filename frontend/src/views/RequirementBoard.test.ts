import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { PageData, Project, Requirement } from '../api'
import { requirementApi } from '../api'
import RequirementBoard from './RequirementBoard.vue'

vi.mock('../api', () => ({ requirementApi: { list: vi.fn() } }))
const a = 'a'.repeat(32)
const b = 'b'.repeat(32)
const projects = [{ id: a, name: '项目A' }, { id: b, name: '项目B' }] as Project[]
const page = (name: string, state = 'NOT_RUN'): PageData<Requirement> => ({
  items: [{ id: name, raw_content: name, analysis_status: state, priority: null }] as Requirement[],
  total: 1, page: 1, page_size: 20,
})
let wrapper: VueWrapper | undefined
const open = () => {
  wrapper = mount(RequirementBoard, {
    props: { projects, selectedProjectId: a },
    global: { plugins: [ElementPlus] },
  })
  return wrapper
}
afterEach(() => {
  wrapper?.unmount()
  vi.useRealTimers()
  vi.clearAllMocks()
})

describe('requirement project scope and analysis updates', () => {
  it('uses the project filter on its very first request and has no batch action', async () => {
    vi.mocked(requirementApi.list).mockResolvedValue(page('项目A需求'))
    const view = open()
    await flushPromises()
    expect(requirementApi.list).toHaveBeenCalledWith(expect.objectContaining({ project_id: a }))
    expect(view.text()).toContain('项目A')
    expect(view.text()).not.toContain('AI批量分析')
  })

  it('never replaces the new project with a delayed response from the old project', async () => {
    let resolveOld!: (value: PageData<Requirement>) => void
    vi.mocked(requirementApi.list)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve }))
      .mockResolvedValueOnce(page('项目B专属需求'))
    const view = open()
    await view.setProps({ selectedProjectId: b })
    await flushPromises()
    resolveOld(page('项目A旧结果'))
    await flushPromises()
    expect(view.text()).toContain('项目B专属需求')
    expect(view.text()).not.toContain('项目A旧结果')
  })

  it('updates a pending analysis automatically and stops polling when it finishes', async () => {
    vi.useFakeTimers()
    vi.mocked(requirementApi.list)
      .mockResolvedValueOnce(page('分析样本', 'PENDING'))
      .mockResolvedValueOnce(page('分析样本', 'ANALYZED'))
    const view = open()
    await flushPromises()
    expect(view.text()).toContain('等待分析')
    await vi.advanceTimersByTimeAsync(1500)
    await flushPromises()
    expect(view.text()).toContain('分析完成')
    await vi.advanceTimersByTimeAsync(5000)
    expect(requirementApi.list).toHaveBeenCalledTimes(2)
  })
})
