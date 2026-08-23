import 'axios'

declare module 'axios' {
  export interface AxiosRequestConfig {
    skipGlobalError?: boolean
    skipAuthRedirect?: boolean
  }

  export interface InternalAxiosRequestConfig {
    skipGlobalError?: boolean
    skipAuthRedirect?: boolean
  }
}
