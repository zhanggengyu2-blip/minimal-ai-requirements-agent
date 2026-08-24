import { expect, test, type Page } from '@playwright/test'

interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
}

interface CurrentSession {
  user: { id: string }
  csrf_token: string
}

const apiBase = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'
const departmentName = process.env.E2E_ADMIN_DEPARTMENT || '产品部'
const adminName = process.env.E2E_ADMIN_NAME || 'E2E管理员'
const sharedPassword = process.env.E2E_SHARED_PASSWORD || 'e2e-shared-password'

const requestApi = async <T>(
  page: Page,
  path: string,
  method = 'GET',
  csrfToken = '',
  body?: Record<string, unknown>,
) => page.evaluate(async ({ url, method, csrfToken, body }) => {
  const response = await fetch(url, {
    method,
    credentials: 'include',
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  return {
    status: response.status,
    payload: await response.json() as ApiEnvelope<T>,
  }
}, { url: `${apiBase}${path}`, method, csrfToken, body })

test('critical task and version flow shares one task across list and gantt views', async ({ page }) => {
  await page.goto('/login')
  await page.getByRole('combobox', { name: '所属部门' }).click()
  await page.getByRole('option', { name: departmentName, exact: true }).click()
  await page.getByRole('textbox', { name: '姓名' }).fill(adminName)
  await page.getByRole('textbox', { name: '公司统一密码' }).fill(sharedPassword)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.getByRole('heading', { name: '项目管理' })).toBeVisible()

  const sessionResponse = await requestApi<CurrentSession>(page, '/auth/me')
  expect(sessionResponse.status).toBe(200)
  const { user, csrf_token: csrfToken } = sessionResponse.payload.data
  const suffix = `${Date.now()}`

  const projectResponse = await requestApi<{ id: string }>(page, '/projects', 'POST', csrfToken, {
    name: `E2E验收项目-${suffix}`,
    project_context: '验证团队任务与版本排期共用同一任务数据',
    description: 'Playwright 临时验收项目',
    member_ids: [user.id],
  })
  expect(projectResponse.status).toBe(201)
  const projectId = projectResponse.payload.data.id

  const versionResponse = await requestApi<{ id: string }>(page, `/projects/${projectId}/versions`, 'POST', csrfToken, {
    name: `V-E2E-${suffix}`,
    start_date: '2026-08-01',
    end_date: '2026-09-30',
    participant_ids: [user.id],
  })
  expect(versionResponse.status).toBe(201)
  const versionId = versionResponse.payload.data.id

  const taskName = `共用任务-${suffix}`
  const completeTask = await requestApi<{ id: string }>(page, `/projects/${projectId}/tasks`, 'POST', csrfToken, {
    name: taskName,
    assignee_id: user.id,
    status: 'IN_PROGRESS',
    priority: 'P1',
    version_id: versionId,
    start_date: '2026-08-20',
    due_date: '2026-08-27',
    description: '在团队任务和版本排期中同步显示',
  })
  expect(completeTask.status).toBe(201)
  const incompleteTask = await requestApi(page, `/projects/${projectId}/tasks`, 'POST', csrfToken, {
    name: `日期不完整任务-${suffix}`,
    assignee_id: user.id,
    status: 'NOT_STARTED',
    priority: 'P2',
    version_id: versionId,
    start_date: '2026-08-28',
    due_date: null,
  })
  expect(incompleteTask.status).toBe(201)

  await page.goto(`/projects/${projectId}/tasks/board`)
  await expect(page.getByText('当前筛选共 2 条任务')).toBeVisible()
  await page.getByRole('button', { name: `查看任务：${taskName}` }).click()
  const updatedTaskName = `已更新共用任务-${suffix}`
  await page.getByPlaceholder('请输入任务名称').fill(updatedTaskName)
  await page.getByRole('button', { name: '保存', exact: true }).click()
  await expect(page.getByRole('button', { name: `查看任务：${updatedTaskName}` })).toBeVisible()

  await page.getByRole('link', { name: '甘特图', exact: true }).click()
  await expect(page.getByRole('button', { name: updatedTaskName, exact: true })).toBeVisible()
  await expect(page.locator('.gantt-task-bar')).toHaveCount(1)
  await expect(page.locator('[draggable="true"]')).toHaveCount(0)

  await page.goto(`/projects/${projectId}/versions/${versionId}/list`)
  await expect(page.getByRole('button', { name: updatedTaskName, exact: true })).toBeVisible()
  await page.getByRole('link', { name: '甘特图', exact: true }).click()
  await expect(page.getByRole('button', { name: updatedTaskName, exact: true })).toBeVisible()
  await expect(page.locator('.gantt-task-bar')).toHaveCount(1)
  await page.locator('[aria-label="甘特图刻度"] button').filter({ hasText: '月' }).click()
  await expect(page.locator('[aria-label="甘特图刻度"] button').filter({ hasText: '月' })).toHaveClass(/active/)
})
