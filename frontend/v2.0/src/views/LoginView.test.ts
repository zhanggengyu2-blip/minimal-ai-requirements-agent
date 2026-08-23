import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from '../api/http'
import LoginView from './LoginView.vue'

const mocks = vi.hoisted(() => ({
  departments: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
}))

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api')
  return {
    ...actual,
    authApi: {
      ...actual.authApi,
      departments: mocks.departments,
    },
  }
})

vi.mock('../composables/useCurrentUser', () => ({
  useCurrentUser: () => ({
    login: mocks.login,
    register: mocks.register,
  }),
}))

const mountLogin = async () => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', component: LoginView },
      { path: '/projects', component: { template: '<div>projects</div>' } },
    ],
  })
  await router.push('/login?redirect=/projects')
  await router.isReady()
  const wrapper = mount(LoginView, {
    global: { plugins: [ElementPlus, router] },
  })
  await flushPromises()
  return wrapper
}

describe('LoginView', () => {
  beforeEach(() => {
    mocks.departments.mockResolvedValue([{ id: 'd'.repeat(32), name: '产品部' }])
    mocks.login.mockReset()
    mocks.register.mockReset()
  })

  it('keeps department and name when switching to first registration', async () => {
    const wrapper = await mountLogin()
    const vm = wrapper.vm as unknown as {
      form: { department_id: string; name: string; credential: string }
      switchMode: (mode: 'login' | 'register') => void
    }
    vm.form.department_id = 'd'.repeat(32)
    vm.form.name = '张三'
    vm.form.credential = 'temporary-secret'
    vm.switchMode('register')
    await wrapper.vm.$nextTick()

    expect(vm.form.department_id).toBe('d'.repeat(32))
    expect(vm.form.name).toBe('张三')
    expect(vm.form.credential).toBe('')
    expect(wrapper.text()).toContain('使用管理员提供的邀请码')
  })

  it('keeps identity fields and clears the secret after a failed login', async () => {
    mocks.login.mockRejectedValue(new ApiRequestError('部门、姓名或统一密码不正确', 401, 'AUTH_IDENTITY_MISMATCH'))
    const wrapper = await mountLogin()
    const vm = wrapper.vm as unknown as {
      form: { department_id: string; name: string; credential: string }
      submit: () => Promise<void>
    }
    vm.form.department_id = 'd'.repeat(32)
    vm.form.name = '张三'
    vm.form.credential = 'wrong-secret'
    await vm.submit()
    await flushPromises()

    expect(mocks.login).toHaveBeenCalledWith({
      department_id: 'd'.repeat(32),
      name: '张三',
      shared_password: 'wrong-secret',
    })
    expect(vm.form.department_id).toBe('d'.repeat(32))
    expect(vm.form.name).toBe('张三')
    expect(vm.form.credential).toBe('')
    expect(wrapper.text()).toContain('部门、姓名或统一密码不正确')
  })
})
