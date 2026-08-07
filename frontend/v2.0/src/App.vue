<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ChatDotRound, Document, Folder, Message, OfficeBuilding, Plus } from '@element-plus/icons-vue'
import type { Department, Project, Requirement } from './api'
import { departmentApi, projectApi, requirementApi } from './api'
import ProjectDialog from './components/ProjectDialog.vue'
import RequirementDialog from './components/RequirementDialog.vue'
import RequirementDetail from './components/RequirementDetail.vue'
import ProjectManagement from './views/ProjectManagement.vue'
import RequirementBoard from './views/RequirementBoard.vue'
import DepartmentManagement from './views/DepartmentManagement.vue'
import InvitationManagement from './views/InvitationManagement.vue'
import InterviewWorkbench from './views/InterviewWorkbench.vue'
import InterviewRecords from './views/InterviewRecords.vue'

const isInterviewWorkbench = window.location.pathname.startsWith('/interviews/workbench')

const currentPage = ref<'requirements' | 'interviews' | 'projects' | 'departments' | 'invitations'>('requirements')
const projects = ref<Project[]>([])
const departments = ref<Department[]>([])
const selectedProjectId = ref<string>()
const expandedProjectIds = ref<Set<string>>(new Set())
const projectDialog = ref(false)
const requirementDialog = ref(false)
const detailDialog = ref(false)
const detailLoading = ref(false)
const detail = ref<Requirement | null>(null)
const boardRef = ref<InstanceType<typeof RequirementBoard>>()
const projectRef = ref<InstanceType<typeof ProjectManagement>>()

const loadProjects = async () => {
  const data = await projectApi.list({ page: 1, page_size: 100, status: 'ACTIVE' })
  const previousProjectIds = new Set(projects.value.map((project) => project.id))
  const availableProjectIds = new Set(data.items.map((project) => project.id))
  const nextExpandedIds = new Set(
    [...expandedProjectIds.value].filter((projectId) => availableProjectIds.has(projectId)),
  )
  data.items.forEach((project) => {
    if (!previousProjectIds.has(project.id)) nextExpandedIds.add(project.id)
  })
  projects.value = data.items
  expandedProjectIds.value = nextExpandedIds
  if (selectedProjectId.value && !projects.value.some((project) => project.id === selectedProjectId.value)) {
    selectedProjectId.value = undefined
  }
}
const loadDepartments = async () => {
  const data = await departmentApi.list({ page: 1, page_size: 100 })
  departments.value = data.items
}
const selectProject = (id?: string) => {
  selectedProjectId.value = id
  currentPage.value = 'requirements'
}
const selectInterviews = (id: string) => {
  selectedProjectId.value = id
  currentPage.value = 'interviews'
}
const isProjectExpanded = (id: string) => expandedProjectIds.value.has(id)
const toggleProject = (id: string) => {
  const nextExpandedIds = new Set(expandedProjectIds.value)
  if (nextExpandedIds.has(id)) nextExpandedIds.delete(id)
  else nextExpandedIds.add(id)
  expandedProjectIds.value = nextExpandedIds
}
const afterProjectCreated = async () => {
  await loadProjects()
  await projectRef.value?.refresh()
}
const afterRequirementCreated = async () => {
  await boardRef.value?.refresh()
  await loadProjects()
}
const showDetail = async (id: string) => {
  detailDialog.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await requirementApi.detail(id)
  } finally {
    detailLoading.value = false
  }
}
onMounted(() => {
  if (!isInterviewWorkbench) {
    loadProjects()
    loadDepartments()
  }
})
</script>

<template>
  <InterviewWorkbench v-if="isInterviewWorkbench" />
  <div v-else class="app-shell unified-shell-mode">
    <header class="topbar">
      <div class="brand">极简 AI 团队需求管理智能体</div>
      <a class="interview-entry" href="/interviews/workbench">进入需求访谈工作台</a>
    </header>
    <div class="body-shell">
      <aside class="sidebar">
        <div class="side-title">
          <button
            type="button"
            class="project-management-entry"
            :class="{ active: currentPage === 'projects' }"
            @click="currentPage = 'projects'"
          >
            <span>项目</span><span class="section-arrow">›</span>
          </button>
          <el-button :icon="Plus" @click="projectDialog = true">新建项目</el-button>
        </div>
        <div class="project-nav">
          <div v-for="project in projects" :key="project.id" class="project-node">
            <button
              class="project-label"
              :aria-expanded="isProjectExpanded(project.id)"
              @click="toggleProject(project.id)"
            >
              <span class="project-caret" :class="{ expanded: isProjectExpanded(project.id) }">›</span>
              <el-icon class="folder"><Folder /></el-icon>
              <span class="project-name">{{ project.name }}</span>
            </button>
            <div v-show="isProjectExpanded(project.id)" class="project-children">
              <button
                class="requirement-link"
                :class="{ active: currentPage === 'requirements' && selectedProjectId === project.id }"
                @click="selectProject(project.id)"
              >
                <el-icon><Document /></el-icon><span>需求</span><em>{{ project.requirement_count }}</em>
              </button>
              <button
                class="requirement-link interview-record-link"
                :class="{ active: currentPage === 'interviews' && selectedProjectId === project.id }"
                @click="selectInterviews(project.id)"
              >
                <el-icon><ChatDotRound /></el-icon><span>访谈记录</span>
              </button>
            </div>
          </div>
          <div v-if="!projects.length" class="side-empty">暂无正常项目</div>
        </div>
        <div class="sidebar-bottom organization-nav">
          <div class="organization-title"><strong>用户与部门</strong><em>管理员专属</em></div>
          <button :class="{ active: currentPage === 'departments' }" @click="currentPage = 'departments'">
            <el-icon><OfficeBuilding /></el-icon><span>部门管理</span>
          </button>
          <button :class="{ active: currentPage === 'invitations' }" @click="currentPage = 'invitations'">
            <el-icon><Message /></el-icon><span>邀请码管理</span>
          </button>
        </div>
      </aside>
      <RequirementBoard
        v-if="currentPage === 'requirements'"
        ref="boardRef"
        :projects="projects"
        :selected-project-id="selectedProjectId"
        @create="requirementDialog = true"
        @detail="showDetail"
      />
      <InterviewRecords
        v-else-if="currentPage === 'interviews'"
        :projects="projects"
        :selected-project-id="selectedProjectId"
      />
      <ProjectManagement
        v-else-if="currentPage === 'projects'"
        ref="projectRef"
        @create="projectDialog = true"
        @changed="loadProjects"
      />
      <DepartmentManagement
        v-else-if="currentPage === 'departments'"
        @changed="loadDepartments"
      />
      <InvitationManagement
        v-else
        :departments="departments"
      />
    </div>

    <ProjectDialog v-model="projectDialog" @created="afterProjectCreated" />
    <RequirementDialog
      v-model="requirementDialog"
      :projects="projects"
      :default-project-id="selectedProjectId"
      @created="afterRequirementCreated"
    />
    <RequirementDetail
      v-model="detailDialog"
      :requirement="detail"
      :projects="projects"
      :loading="detailLoading"
    />
  </div>
</template>
