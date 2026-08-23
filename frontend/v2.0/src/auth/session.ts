import { computed, readonly, ref } from 'vue'
import type { CurrentUser } from '../api'

const currentUserState = ref<CurrentUser | null>(null)
const csrfTokenState = ref<string | null>(null)

export const currentUser = readonly(currentUserState)
export const csrfToken = readonly(csrfTokenState)
export const isAuthenticated = computed(() => currentUserState.value !== null)
export const isAdmin = computed(() => currentUserState.value?.role === 'ADMIN')

export const setSession = (user: CurrentUser, csrf: string) => {
  currentUserState.value = user
  csrfTokenState.value = csrf
}

export const clearSession = () => {
  currentUserState.value = null
  csrfTokenState.value = null
}

export const getCsrfToken = () => csrfTokenState.value
