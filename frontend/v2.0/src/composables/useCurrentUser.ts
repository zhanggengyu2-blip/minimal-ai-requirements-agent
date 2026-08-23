import { authApi, type LoginRequest, type RegistrationRequest } from '../api'
import { ApiRequestError } from '../api/http'
import {
  clearSession,
  csrfToken,
  currentUser,
  isAdmin,
  isAuthenticated,
  setSession,
} from '../auth/session'

let initialized = false
let loadingSession: Promise<void> | null = null

const applySession = (session: Awaited<ReturnType<typeof authApi.me>>) => {
  setSession(session.user, session.csrf_token)
}

const ensureSession = async (force = false) => {
  if (initialized && !force) return currentUser.value
  if (loadingSession) {
    await loadingSession
    return currentUser.value
  }

  loadingSession = (async () => {
    try {
      applySession(await authApi.me())
      initialized = true
    } catch (error) {
      if (!(error instanceof ApiRequestError) || error.status !== 401) throw error
      clearSession()
      initialized = true
    } finally {
      loadingSession = null
    }
  })()
  await loadingSession
  return currentUser.value
}

const login = async (payload: LoginRequest) => {
  const session = await authApi.login(payload)
  applySession(session)
  initialized = true
  return session.user
}

const register = async (payload: RegistrationRequest) => {
  const session = await authApi.register(payload)
  applySession(session)
  initialized = true
  return session.user
}

const logout = async () => {
  try {
    await authApi.logout()
  } finally {
    clearSession()
    initialized = true
  }
}

export const resetCurrentUserState = () => {
  clearSession()
  initialized = false
  loadingSession = null
}

export const useCurrentUser = () => ({
  currentUser,
  csrfToken,
  isAuthenticated,
  isAdmin,
  ensureSession,
  login,
  register,
  logout,
})
