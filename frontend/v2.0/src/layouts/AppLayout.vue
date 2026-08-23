<script setup lang="ts">
import { computed, onMounted, provide, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Calendar,
  ChatDotRound,
  Document,
  Folder,
  Message,
  OfficeBuilding,
  Operation,
  Plus,
  SwitchButton,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { projectApi, type Project } from '../api'
import { useCurrentUser } from '../composables/useCurrentUser'
import ProjectDialog from '../components/ProjectDialog.vue'
import { appShellKey } from './appShell'

const route = useRoute()
const router = useRouter()
const auth = useCurrentUser()
const projects = ref<Project[]>([])
const projectsLoading = ref(false)
const projectListRevision = ref(0)
const projectDialog = ref(false)
const expandedProjectIds = ref<Set<string>>(new Set())
const archivedExpanded = ref(false)

const activeProjects = computed(() => projects.value.filter((item) => item.status === 'ACTIVE'))
const archivedProjects = computed(() => projects.value.filter((item) => item.status === 'ARCHIVED'))
const currentProjectId = computed(() => String(route.params.projectId || ''))

const refreshProjects = async () => {
  projectsLoading.value = true
  try {
    const previousIds = new Set(projects.value.map((item) => item.id))
    const [active, archived] = await Promise.all([
      projectApi.list({ page: 1, page_size: 100, status: 'ACTIVE' }),
      projectApi.list({ page: 1, page_size: 100, status: 'ARCHIVED' }),
    ])
    projects.value = [...active.items, ...archived.items]
    const validIds = new Set(projects.value.map((item) => item.id))
    const nextExpandedIds = new Set(
      [...expandedProjectIds.value].filter((id) => validIds.has(id)),
    )
    projects.value.forEach((item) => {
      if (!previousIds.has(item.id) && item.status === 'ACTIVE') nextExpandedIds.add(item.id)
    })
    expandedProjectIds.value = nextExpandedIds
    if (currentProjectId.value && validIds.has(currentProjectId.value)) {
      expandedProjectIds.value.add(currentProjectId.value)
      const current = projects.value.find((item) => item.id === currentProjectId.value)
      if (current?.status === 'ARCHIVED') archivedExpanded.value = true
    }
  } finally {
    projectsLoading.value = false
  }
}

const toggleProject = (projectId: string) => {
  const next = new Set(expandedProjectIds.value)
  if (next.has(projectId)) next.delete(projectId)
  else next.add(projectId)
  expandedProjectIds.value = next
}

const isRouteActive = (projectId: string, routeNames: string[]) =>
  currentProjectId.value === projectId && routeNames.includes(String(route.name || ''))

const openProjectDialog = () => { projectDialog.value = true }
const afterProjectCreated = async () => {
  await refreshProjects()
  projectListRevision.value += 1
}
const logout = async () => {
  await auth.logout()
  ElMessage.success('已退出登录')
  await router.replace({ name: 'login' })
}

provide(appShellKey, {
  projects,
  projectsLoading,
  projectListRevision,
  refreshProjects,
  openProjectDialog,
})

watch(currentProjectId, (projectId) => {
  if (!projectId) return
  const next = new Set(expandedProjectIds.value)
  next.add(projectId)
  expandedProjectIds.value = next
})
onMounted(refreshProjects)
</script>

<template>
  <div class="app-shell routed-app-shell">
    <header class="topbar app-topbar">
      <RouterLink class="brand brand-link" :to="{ name: 'projects' }">极简 AI 团队需求管理智能体</RouterLink>
      <RouterLink class="interview-entry" :to="{ name: 'interview-workbench' }">进入需求访谈工作台</RouterLink>
      <el-dropdown trigger="click" class="user-menu">
        <button type="button" class="user-menu-trigger">
          <span class="user-avatar">{{ auth.currentUser.value?.name.slice(0, 1) }}</span>
          <span class="user-summary">
            <strong>{{ auth.currentUser.value?.name }}</strong>
            <small>{{ auth.currentUser.value?.department_name }} · {{ auth.isAdmin.value ? '管理员' : '成员' }}</small>
          </span>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item :icon="SwitchButton" @click="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </header>

    <div class="body-shell">
      <aside class="sidebar routed-sidebar">
        <div class="side-title">
          <RouterLink class="project-management-entry" :class="{ active: route.name === 'projects' }" :to="{ name: 'projects' }">
            <span>项目</span><span class="section-arrow">›</span>
          </RouterLink>
          <el-button :icon="Plus" @click="openProjectDialog">新建项目</el-button>
        </div>

        <div v-loading="projectsLoading" class="project-nav routed-project-nav">
          <template v-for="project in activeProjects" :key="project.id">
            <div class="project-node">
              <button class="project-label" :aria-expanded="expandedProjectIds.has(project.id)" @click="toggleProject(project.id)">
                <span class="project-caret" :class="{ expanded: expandedProjectIds.has(project.id) }">›</span>
                <el-icon class="folder"><Folder /></el-icon>
                <span class="project-name">{{ project.name }}</span>
              </button>
              <div v-show="expandedProjectIds.has(project.id)" class="project-children">
                <RouterLink class="requirement-link" :class="{ active: isRouteActive(project.id, ['project-requirements']) }" :to="{ name: 'project-requirements', params: { projectId: project.id } }">
                  <el-icon><Document /></el-icon><span>需求</span><em>{{ project.requirement_count }}</em>
                </RouterLink>
                <RouterLink class="requirement-link" :class="{ active: isRouteActive(project.id, ['project-interviews']) }" :to="{ name: 'project-interviews', params: { projectId: project.id } }">
                  <el-icon><ChatDotRound /></el-icon><span>访谈记录</span>
                </RouterLink>
                <RouterLink class="requirement-link" :class="{ active: isRouteActive(project.id, ['project-task-board', 'project-task-gantt']) }" :to="{ name: 'project-task-board', params: { projectId: project.id } }">
                  <el-icon><Operation /></el-icon><span>团队任务</span>
                </RouterLink>
                <RouterLink class="requirement-link" :class="{ active: isRouteActive(project.id, ['project-versions', 'project-version-list', 'project-version-gantt']) }" :to="{ name: 'project-versions', params: { projectId: project.id } }">
                  <el-icon><Calendar /></el-icon><span>版本排期</span>
                </RouterLink>
              </div>
            </div>
          </template>
          <div v-if="!projectsLoading && !activeProjects.length" class="side-empty">暂无正常项目</div>

          <section v-if="archivedProjects.length" class="archived-projects">
            <button type="button" class="archived-projects-toggle" @click="archivedExpanded = !archivedExpanded">
              <span>已归档项目</span><em>{{ archivedProjects.length }}</em><span class="project-caret" :class="{ expanded: archivedExpanded }">›</span>
            </button>
            <div v-show="archivedExpanded">
              <div v-for="project in archivedProjects" :key="project.id" class="project-node archived-project-node">
                <button class="project-label" :aria-expanded="expandedProjectIds.has(project.id)" @click="toggleProject(project.id)">
                  <span class="project-caret" :class="{ expanded: expandedProjectIds.has(project.id) }">›</span>
                  <el-icon class="folder"><Folder /></el-icon>
                  <span class="project-name">{{ project.name }}</span>
                  <em class="archive-badge">归档</em>
                </button>
                <div v-show="expandedProjectIds.has(project.id)" class="project-children">
                  <RouterLink class="requirement-link" :class="{ active: isRouteActive(project.id, ['project-requirements']) }" :to="{ name: 'project-requirements', params: { projectId: project.id } }">
                    <el-icon><Document /></el-icon><span>需求</span>
                  </RouterLink>
                  <RouterLink class="requirement-link" :class="{ active: isRouteActive(project.id, ['project-interviews']) }" :to="{ name: 'project-interviews', params: { projectId: project.id } }">
                    <el-icon><ChatDotRound /></el-icon><span>访谈记录</span>
                  </RouterLink>
                  <RouterLink class="requirement-link" :class="{ active: isRouteActive(project.id, ['project-task-board', 'project-task-gantt']) }" :to="{ name: 'project-task-board', params: { projectId: project.id } }">
                    <el-icon><Operation /></el-icon><span>团队任务</span>
                  </RouterLink>
                  <RouterLink class="requirement-link" :class="{ active: isRouteActive(project.id, ['project-versions', 'project-version-list', 'project-version-gantt']) }" :to="{ name: 'project-versions', params: { projectId: project.id } }">
                    <el-icon><Calendar /></el-icon><span>版本排期</span>
                  </RouterLink>
                </div>
              </div>
            </div>
          </section>
        </div>

        <div v-if="auth.isAdmin.value" class="sidebar-bottom organization-nav">
          <div class="organization-title"><strong>用户与部门</strong><em>管理员专属</em></div>
          <RouterLink class="organization-link" :class="{ active: route.name === 'admin-departments' }" :to="{ name: 'admin-departments' }">
            <el-icon><OfficeBuilding /></el-icon><span>部门管理</span>
          </RouterLink>
          <RouterLink class="organization-link" :class="{ active: route.name === 'admin-invitations' }" :to="{ name: 'admin-invitations' }">
            <el-icon><Message /></el-icon><span>邀请码管理</span>
          </RouterLink>
        </div>
      </aside>

      <RouterView />
    </div>

    <ProjectDialog v-model="projectDialog" @created="afterProjectCreated" />
  </div>
</template>
