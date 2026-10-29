import type {
  NavigationGuardReturn,
  RouteLocationNormalized,
  Router,
} from 'vue-router'
import type { CurrentUser } from '../api'
import { useCurrentUser } from '../composables/useCurrentUser'
import { useProjectAccess } from '../composables/useProjectAccess'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    guestOnly?: boolean
    adminOnly?: boolean
    projectRoute?: boolean
    placeholderTitle?: string
    placeholderDescription?: string
  }
}

const safeReturnPath = (path: string) =>
  path.startsWith('/') && !path.startsWith('//') ? path : '/projects'

export const routeAccessDecision = (
  to: Pick<RouteLocationNormalized, 'name' | 'fullPath' | 'meta'>,
  user: CurrentUser | null,
): NavigationGuardReturn => {
  if (to.meta.guestOnly && user) return { name: 'projects' }
  if (to.meta.requiresAuth && !user) {
    return {
      name: 'login',
      query: { redirect: safeReturnPath(to.fullPath) },
    }
  }
  if (to.meta.adminOnly && user?.role !== 'ADMIN') return { name: 'projects' }
  return true
}

export const installRouteGuards = (router: Router) => {
  router.beforeEach(async (to) => {
    const auth = useCurrentUser()
    let user: CurrentUser | null
    try {
      user = await auth.ensureSession()
    } catch {
      if (!to.meta.requiresAuth) return true
      return {
        name: 'login',
        query: { redirect: safeReturnPath(to.fullPath) },
      }
    }
    const accessDecision = routeAccessDecision(to, user)
    if (accessDecision !== true) return accessDecision

    const projectAccess = useProjectAccess()
    if (to.meta.projectRoute) {
      const projectId = String(to.params.projectId || '')
      if (!projectId || !(await projectAccess.loadProjectAccess(projectId))) {
        return { name: 'not-found', replace: true }
      }
    } else {
      projectAccess.clearProjectAccess()
    }
    return true
  })
}
