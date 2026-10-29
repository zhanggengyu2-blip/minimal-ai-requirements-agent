import axios, { AxiosError } from 'axios'
import { ElMessage } from 'element-plus'
import { clearSession, getCsrfToken } from '../auth/session'

interface ErrorBody {
  code?: string
  message?: string
  details?: unknown
  request_id?: string
}

interface ValidationDetail {
  loc?: Array<string | number>
  msg?: string
}

interface HttpNavigationHandlers {
  onUnauthorized?: (returnTo: string) => void | Promise<void>
  onProjectArchived?: () => void | Promise<void>
}

let navigationHandlers: HttpNavigationHandlers = {}

export const configureHttpNavigation = (handlers: HttpNavigationHandlers) => {
  navigationHandlers = handlers
}

export class ApiRequestError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    readonly code?: string,
    readonly details?: unknown,
    readonly requestId?: string,
  ) {
    super(message)
    this.name = 'ApiRequestError'
  }
}

export const isApiRequestError = (error: unknown): error is ApiRequestError =>
  error instanceof ApiRequestError

const writeMethods = new Set(['post', 'put', 'patch', 'delete'])
const isRevisionConflict = (code?: string) =>
  Boolean(code && (code.includes('REVISION_CONFLICT') || code === 'LANE_REVISION_CONFLICT'))

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'
const apiOrigin = (() => {
  try {
    return new URL(apiBaseUrl, window.location.origin).origin
  } catch {
    return apiBaseUrl
  }
})()

export const http = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config) => {
  config.headers['X-Request-ID'] = crypto.randomUUID().replaceAll('-', '')
  if (writeMethods.has(config.method?.toLowerCase() || '')) {
    const csrf = getCsrfToken()
    if (csrf) config.headers['X-CSRF-Token'] = csrf
  }
  return config
})

http.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body && typeof body === 'object' && 'code' in body) {
      const savedWithAnalysisFailure = body.code === 'AI_ANALYSIS_FAILED'
        && body.data?.id && body.data.analysis_status === 'FAILED'
      if (body.code !== 'OK' && !savedWithAnalysisFailure) {
        return Promise.reject(new Error(body.message || '请求处理失败'))
      }
      return body.data
    }
    return body
  },
  (error: AxiosError<ErrorBody>) => {
    const status = error.response?.status
    const body = error.response?.data
    let message = body?.message || error.message || '网络请求失败'

    if (status === 422) {
      const details = Array.isArray(body?.details) ? body.details as ValidationDetail[] : []
      const detail = details[0]
      const field = detail?.loc?.at(-1)
      message = detail?.msg ? `${field ? `${field}：` : ''}${detail.msg}` : '提交内容不符合校验规则，请检查后重试'
    } else if (status === 404) {
      message = body?.message || '访问的数据不存在或已被删除'
    } else if (body?.code === 'AI_ANALYSIS_FAILED' || body?.code?.startsWith('DIFY_')) {
      message = '需求保存成功，但AI分析失败，可稍后重试'
    } else if (!error.response) {
      message = `无法连接后端服务，请确认 ${apiOrigin} 已启动`
    }

    if (status === 401) {
      clearSession()
      if (!error.config?.skipAuthRedirect) {
        const returnTo = `${window.location.pathname}${window.location.search}${window.location.hash}`
        void navigationHandlers.onUnauthorized?.(returnTo)
      }
    }
    if (status === 403 && body?.code === 'PROJECT_ARCHIVED') {
      void navigationHandlers.onProjectArchived?.()
    }

    const shouldShowMessage = !error.config?.skipGlobalError
      && status !== 401
      && !isRevisionConflict(body?.code)
    if (shouldShowMessage) ElMessage.error({ message, duration: 4200 })

    return Promise.reject(new ApiRequestError(
      message,
      status,
      body?.code,
      body?.details,
      body?.request_id || error.response?.headers['x-request-id'],
    ))
  },
)
