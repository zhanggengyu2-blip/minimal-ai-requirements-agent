import axios, { AxiosError } from 'axios'
import { ElMessage } from 'element-plus'

interface ErrorBody {
  code?: string
  message?: string
  details?: Array<{ loc?: Array<string | number>; msg?: string }>
}

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config) => {
  config.headers['X-Request-ID'] = crypto.randomUUID().replaceAll('-', '')
  return config
})

http.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code !== 'OK') {
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
      const detail = body?.details?.[0]
      const field = detail?.loc?.at(-1)
      message = detail?.msg ? `${field ? `${field}：` : ''}${detail.msg}` : '提交内容不符合校验规则，请检查后重试'
    } else if (status === 404) {
      message = body?.message || '访问的数据不存在或已被删除'
    } else if (body?.code === 'AI_ANALYSIS_FAILED' || body?.code?.startsWith('DIFY_')) {
      message = '需求保存成功，但AI分析失败，可稍后重试'
    } else if (!error.response) {
      message = '无法连接本地后端，请确认服务已在 127.0.0.1:8000 启动'
    }

    ElMessage.error({ message, duration: 4200 })
    return Promise.reject(error)
  },
)
