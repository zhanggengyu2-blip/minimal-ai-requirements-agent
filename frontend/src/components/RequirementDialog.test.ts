import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import ElementPlus, { ElButton, ElInput, ElSwitch } from 'element-plus'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Project, Requirement } from '../api'
import { requirementApi } from '../api'
import RequirementDialog from './RequirementDialog.vue'

vi.mock('../api', () => ({ requirementApi: { create: vi.fn() } }))
let wrapper: VueWrapper | undefined
const projects = [{ id: 'a'.repeat(32), name: '测试项目', status: 'ACTIVE' }] as Project[]

const open = async () => {
  wrapper = mount(RequirementDialog, {
    props: { modelValue: false, projects, defaultProjectId: projects[0].id },
    attachTo: document.body,
    global: { plugins: [ElementPlus] },
  })
  await wrapper.setProps({ modelValue: true })
  await flushPromises()
  await wrapper.findComponent(ElInput).setValue('测试需求：保存和分析结果必须明确区分。')
  return wrapper
}
const submit = (view: VueWrapper) => view.findAllComponents(ElButton)
  .find((button) => button.text() === '提交需求')!.trigger('click')

afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
  vi.clearAllMocks()
})

describe('requirement saving and optional AI analysis', () => {
  it('defaults to saving only and resets the switch on reopening', async () => {
    vi.mocked(requirementApi.create).mockResolvedValue({ analysis_status: 'NOT_RUN' } as Requirement)
    const view = await open()
    expect(view.findComponent(ElSwitch).props('modelValue')).toBe(false)
    await submit(view)
    await flushPromises()
    expect(requirementApi.create).toHaveBeenCalledWith(expect.objectContaining({ analyze_with_ai: false }))
    expect(document.body.textContent).toContain('需求已保存，未开启 AI 分析')
    expect(view.emitted('update:modelValue')).toContainEqual([false])
    await view.findComponent(ElSwitch).find('input').setValue(true)
    await view.setProps({ modelValue: false })
    await view.setProps({ modelValue: true })
    expect(view.findComponent(ElSwitch).props('modelValue')).toBe(false)
  })

  it.each([
    ['PENDING', '需求已保存，AI 分析结果稍后自动更新'],
    ['FAILED', '需求已保存，但 AI 分析失败'],
    ['ANALYZED', '需求提交成功，AI 分析已完成'],
  ] as const)('closes after a saved %s response and refreshes the parent', async (state, message) => {
    vi.mocked(requirementApi.create).mockResolvedValue({ analysis_status: state } as Requirement)
    const view = await open()
    await view.findComponent(ElSwitch).find('input').setValue(true)
    await submit(view)
    await flushPromises()
    expect(requirementApi.create).toHaveBeenCalledWith(expect.objectContaining({ analyze_with_ai: true }))
    expect(document.body.textContent).toContain(message)
    expect(view.emitted('created')).toContainEqual([state === 'FAILED'])
    expect(view.emitted('update:modelValue')).toContainEqual([false])
  })

  it('keeps the form open after saving itself fails', async () => {
    vi.mocked(requirementApi.create).mockRejectedValue(new Error('save failed'))
    const view = await open()
    await submit(view)
    await flushPromises()
    expect(view.emitted('created')).toBeUndefined()
    expect(view.emitted('update:modelValue')).toBeUndefined()
    expect(view.findComponent(ElInput).props('modelValue')).toContain('测试需求')
  })
})
