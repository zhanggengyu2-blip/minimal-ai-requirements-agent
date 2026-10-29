import type { InjectionKey, Ref } from 'vue'
import { inject } from 'vue'
import type { Project } from '../api'

export interface AppShellContext {
  projects: Readonly<Ref<Project[]>>
  projectsLoading: Readonly<Ref<boolean>>
  projectListRevision: Readonly<Ref<number>>
  refreshProjects: () => Promise<void>
  openProjectDialog: () => void
}

export const appShellKey: InjectionKey<AppShellContext> = Symbol('app-shell')

export const useAppShell = () => {
  const context = inject(appShellKey)
  if (!context) throw new Error('App shell context is unavailable')
  return context
}
