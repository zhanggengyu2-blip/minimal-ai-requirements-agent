<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Document, Folder, Management, Message, OfficeBuilding, Plus } from '@element-plus/icons-vue'
import type { Department, Project, Requirement } from './api'
import { departmentApi, projectApi, requirementApi } from './api'
import ProjectDialog from './components/ProjectDialog.vue'
import RequirementDialog from './components/RequirementDialog.vue'
import RequirementDetail from './components/RequirementDetail.vue'
import ProjectManagement from './views/ProjectManagement.vue'
import RequirementBoard from './views/RequirementBoard.vue'
import DepartmentManagement from './views/DepartmentManagement.vue'
import InvitationManagement from './views/InvitationManagement.vue'

const currentPage = ref<'requirements' | 'projects' | 'departments' | 'invitations'>('requirements')
const projects = ref<Project[]>([])
const departments = ref<Department[]>([])
const selectedProjectId = ref<string>()
const projectDialog = ref(false)
const requirementDialog = ref(false)
const detailDialog = ref(false)
const detailLoading = ref(false)
const detail = ref<Requirement | null>(null)
const boardRef = ref<InstanceType<typeof RequirementBoard>>()
const projectRef = ref<InstanceType<typeof ProjectManagement>>()

const loadProjects = async () => {
  const data = await projectApi.list({ page: 1, page_size: 100, status: 'ACTIVE' })
  projects.value = data.items
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
  loadProjects()
  loadDepartments()
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">极简 AI 团队需求管理智能体</div>
    </header>
    <div class="body-shell">
      <aside class="sidebar">
        <div class="side-title">
          <strong>项目</strong>
          <el-button :icon="Plus" @click="projectDialog = true">新建项目</el-button>
        </div>
        <button class="side-all" :class="{ active: currentPage === 'projects' }" @click="currentPage = 'projects'">
          <el-icon><Management /></el-icon><span>项目管理</span>
        </button>
        <div class="project-nav">
          <div v-for="project in projects" :key="project.id" class="project-node">
            <button class="project-label" @click="selectProject(project.id)">
              <el-icon class="folder"><Folder /></el-icon>
              <span>{{ project.name }}</span>
            </button>
            <button
              class="requirement-link"
              :class="{ active: currentPage === 'requirements' && selectedProjectId === project.id }"
              @click="selectProject(project.id)"
            >
              <el-icon><Document /></el-icon><span>需求</span><em>{{ project.requirement_count }}</em>
            </button>
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
