<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute } from 'vue-router'
import { Plus, Search } from '@element-plus/icons-vue'
import GanttShell from '../components/GanttShell.vue'
import TaskDialog from '../components/TaskDialog.vue'
import {
  taskApi,
  versionApi,
  type Task,
  type TaskStatusFilter,
  type VersionSummary,
} from '../api'
import { ApiRequestError } from '../api/http'
import { useProjectAccess } from '../composables/useProjectAccess'
import { useTeamTaskModuleState } from '../composables/useTaskModuleState'

const route = useRoute()
const access = useProjectAccess()
const moduleState = useTeamTaskModuleState()
const projectId = computed(() => String(route.params.projectId || ''))
const projectName = computed(() => access.project.value?.name || '当前项目')
const members = computed(() => access.members.value?.items || [])
const { keyword, status, scale } = moduleState
const tasks = ref<Task[]>([])
const versions = ref<VersionSummary[]>([])
const total = ref(0)
const loading = ref(true)
const loadError = ref('')
const taskDialogVisible = ref(false)
const selectedTask = ref<Task | null>(null)
let loadSequence = 0

const statusOptions: Array<{ label: string; value: TaskStatusFilter }> = [
  { label: '未完成任务', value: 'UNFINISHED' },
  { label: '全部状态', value: 'ALL' },
  { label: '未开始', value: 'NOT_STARTED' },
  { label: '进行中', value: 'IN_PROGRESS' },
  { label: '已完成', value: 'COMPLETED' },
  { label: '已取消', value: 'CANCELED' },
]
const versionNames = computed(() => new Map(versions.value.map((version) => [version.id, version.name])))
const describeError = (error: unknown) => error instanceof ApiRequestError ? error.message : '团队任务甘特图加载失败'

const loadTasks = async () => {
  if (!projectId.value) return
  const sequence = ++loadSequence
  loading.value = true
  loadError.value = ''
  try {
    const data = await taskApi.list(projectId.value, {
      keyword: keyword.value.trim() || undefined,
      status: status.value,
    })
    if (sequence === loadSequence) {
      tasks.value = data.items
      total.value = data.total
    }
  } catch (error) {
    if (sequence === loadSequence) loadError.value = describeError(error)
  } finally {
    if (sequence === loadSequence) loading.value = false
  }
}
const initialize = async () => {
  moduleState.ensureProject(projectId.value)
  loading.value = true
  loadError.value = ''
  try {
    if (!access.project.value || access.project.value.id !== projectId.value) {
      await access.loadProjectAccess(projectId.value)
    }
    const [versionList] = await Promise.all([
      versionApi.list(projectId.value).catch(() => ({ items: [], total: 0 })),
      loadTasks(),
    ])
    versions.value = versionList.items
  } catch (error) {
    loadError.value = describeError(error)
  } finally {
    loading.value = false
  }
}
let searchTimer: ReturnType<typeof setTimeout> | undefined
const delayedSearch = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void loadTasks(), 300)
}
const openCreate = () => {
  if (access.readOnly.value) return
  selectedTask.value = null
  taskDialogVisible.value = true
}
const openTask = (task: Task) => {
  selectedTask.value = task
  taskDialogVisible.value = true
}

watch(projectId, () => void initialize())
watch(status, () => void loadTasks())
onMounted(initialize)
onBeforeUnmount(() => clearTimeout(searchTimer))
onBeforeRouteLeave((to) => {
  const staysInModule = ['project-task-board', 'project-task-gantt'].includes(String(to.name || ''))
    && String(to.params.projectId || '') === projectId.value
  if (!staysInModule) moduleState.reset()
})
</script>

<template>
  <main class="page team-gantt-page">
    <el-alert
      v-if="access.readOnly.value"
      title="项目已归档或当前账号不是项目成员，仅支持查看任务"
      type="warning"
      show-icon
      :closable="false"
      class="readonly-alert"
    />
    <div class="team-task-heading">
      <div class="breadcrumb-title team-task-breadcrumb"><strong>{{ projectName }}</strong><span>/</span><strong>团队任务</strong></div>
      <span class="team-task-total">当前筛选共 {{ total }} 条任务</span>
    </div>
    <div class="team-task-toolbar">
      <nav class="task-view-tabs" aria-label="团队任务视图">
        <RouterLink :to="{ name: 'project-task-board', params: { projectId } }">任务面板</RouterLink>
        <RouterLink :to="{ name: 'project-task-gantt', params: { projectId } }" class="active">甘特图</RouterLink>
      </nav>
      <el-input v-model="keyword" :prefix-icon="Search" maxlength="100" clearable placeholder="搜索任务名称" class="task-search" @input="delayedSearch" @clear="loadTasks" />
      <el-select v-model="status" class="task-status-filter" aria-label="筛选任务状态">
        <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
      </el-select>
      <el-button type="primary" :icon="Plus" :disabled="access.readOnly.value || !members.length" @click="openCreate">新建任务</el-button>
    </div>

    <section v-if="loadError" class="gantt-error-state">
      <el-result icon="error" title="甘特图加载失败" :sub-title="loadError"><template #extra><el-button type="primary" @click="initialize">重新加载</el-button></template></el-result>
    </section>
    <GanttShell v-else v-model:scale="scale" :members="members" :tasks="tasks" :version-names="versionNames" :loading="loading" @open="openTask" />

    <TaskDialog v-model="taskDialogVisible" :project-id="projectId" :members="members" :versions="versions" :task="selectedTask" :read-only="access.readOnly.value" @changed="loadTasks" />
  </main>
</template>
