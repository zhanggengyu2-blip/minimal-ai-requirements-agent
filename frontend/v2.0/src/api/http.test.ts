import { afterEach, describe, expect, it } from 'vitest'
import type { InternalAxiosRequestConfig } from 'axios'
import { clearSession, setSession } from '../auth/session'
import { http } from './http'

afterEach(clearSession)

describe('authenticated HTTP client', () => {
  it('uses credentialed requests and attaches CSRF only to writes', async () => {
    setSession({
      id: '1'.repeat(32),
      department_id: '2'.repeat(32),
      department_name: '产品部',
      name: '测试成员',
      role: 'MEMBER',
      created_time: '2026-08-23T00:00:00Z',
    }, 'csrf-test-token')

    const seen: InternalAxiosRequestConfig[] = []
    const adapter = async (config: InternalAxiosRequestConfig) => {
      seen.push(config)
      return {
        data: { code: 'OK', message: 'ok', data: {} },
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      }
    }

    await http.get('/probe', { adapter })
    await http.post('/probe', {}, { adapter })

    expect(http.defaults.withCredentials).toBe(true)
    expect(seen[0].headers['X-Request-ID']).toBeTruthy()
    expect(seen[0].headers['X-CSRF-Token']).toBeUndefined()
    expect(seen[1].headers['X-CSRF-Token']).toBe('csrf-test-token')
  })
})
