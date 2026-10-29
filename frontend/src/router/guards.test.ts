import { describe, expect, it } from 'vitest'
import type { RouteLocationNormalized } from 'vue-router'
import type { CurrentUser } from '../api'
import { routeAccessDecision } from './guards'

const member: CurrentUser = {
  id: '1'.repeat(32),
  department_id: '2'.repeat(32),
  department_name: '产品部',
  name: '普通成员',
  role: 'MEMBER',
  created_time: '2026-08-23T00:00:00Z',
}
const admin: CurrentUser = { ...member, id: '3'.repeat(32), name: '管理员', role: 'ADMIN' }
const target = (
  meta: RouteLocationNormalized['meta'],
  fullPath = '/projects/abc/tasks/board',
  name: RouteLocationNormalized['name'] = 'target',
) => ({ meta, fullPath, name })

describe('route access decisions', () => {
  it('sends unauthenticated users to login and preserves the return address', () => {
    expect(routeAccessDecision(target({ requiresAuth: true }), null)).toEqual({
      name: 'login',
      query: { redirect: '/projects/abc/tasks/board' },
    })
  })

  it('blocks ordinary members from administrator pages', () => {
    expect(routeAccessDecision(target({ requiresAuth: true, adminOnly: true }), member))
      .toEqual({ name: 'projects' })
    expect(routeAccessDecision(target({ requiresAuth: true, adminOnly: true }), admin)).toBe(true)
  })

  it('redirects an authenticated user away from login', () => {
    expect(routeAccessDecision(target({ guestOnly: true }, '/login', 'login'), member))
      .toEqual({ name: 'projects' })
  })

  it('does not accept a protocol-relative return address', () => {
    expect(routeAccessDecision(target({ requiresAuth: true }, '//evil.example'), null)).toEqual({
      name: 'login',
      query: { redirect: '/projects' },
    })
  })
})
