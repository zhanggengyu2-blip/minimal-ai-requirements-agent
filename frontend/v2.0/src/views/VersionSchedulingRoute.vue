<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Calendar, EditPen, Plus, Search, User } from '@element-plus/icons-vue'
import TaskDialog from '../components/TaskDialog.vue'
import VersionDialog from '../components/VersionDialog.vue'
import {
  taskApi,
  versionApi,
  type ProjectVersion,
  type Task,
  type TaskStatus,
  type TaskStatusFilter,
  type VersionCompletionImpact,
  type VersionStatus,
  type VersionSummary,
} from '../api'
import { ApiRequestError } from '../api/http'
import { useProjectAccess } from '../composables/useProjectAccess'

const route = useRoute()
const router = useRouter()
const access = useProjectAccess()
const projectId = computed(() => String(route.params.projectId || ''))
const routeVersionId = computed(() => String(route.params.versionId || ''))
const projectName = computed(() => access.project.value?.name || '当前项目')
const projectMembers = computed(() => access.members.value?.items || [])
const loading = ref(true)
const loadError = ref('')
const versions = ref<VersionSummary[]>([])
const currentVersion = ref<ProjectVersion | null>(null)
const tasks = ref<Task[]>([])
const total = ref(0)
const keyword = ref('')
const status = ref<TaskStatusFilter>('ALL')
const versionDialogVisible = ref(false)
const editingVersion = ref<ProjectVersion | null>(null)
const taskDialogVisible = ref(false)
const selectedTask = ref<Task | null>(null)
const initialAssigneeId = ref('')
const completionVisible = ref(false)
const completionImpact = ref<VersionCompletionImpact | null>(null)
const completionLoading = ref(false)
const statusUpdating = ref(false)
const deleteVisible = ref(false)
const deleting = ref(false)
let loadSequence = 0

const statusOptions: Array<{ label: string; value: TaskStatusFilter }> = [
  { label: '全部状态', value: 'ALL' },
  { label: '未完成任务', value: 'UNFINISHED' },
  { label: '未开始', value: 'NOT_STARTED' },
  { label: '进行中', value: 'IN_PROGRESS' },
  { label: '已完成', value: 'COMPLETED' },
  { label: '已取消', value: 'CANCELED' },
]
const versionStatusMeta: Record<VersionStatus, { label: string; className: string }> = {
  NOT_STARTED: { label: '未开始', className: 'not-started' },
  IN_PROGRESS: { label: '进行中', className: 'in-progress' },
  COMPLETED: { label: '已完成', className: 'completed' },
}
const taskStatusMeta: Record<TaskStatus, { label: string; className: string }> = {
  NOT_STARTED: { label: '未开始', className: 'not-started' },
  IN_PROGRESS: { label: '进行中', className: 'in-progress' },
  COMPLETED: { label: '已完成', className: 'completed' },
  CANCELED: { label: '已取消', className: 'canceled' },
}
const currentStatus = computed(() => currentVersion.value ? versionStatusMeta[currentVersion.value.status] : null)
const groupedTasks = computed(() => {
  const groups = new Map<string, Task[]>()
  currentVersion.value?.participants.forEach((participant) => groups.set(participant.user_id, []))
  tasks.value.forEach((task) => groups.get(task.assignee_id)?.push(task))
  return groups
})
const ganttQuery = computed(() => ({
  ...(keyword.value.trim() ? { keyword: keyword.value.trim() } : {}),
  ...(status.value !== 'ALL' ? { status: status.value } : {}),
}))

const describeError = (error: unknown, fallback: string) =>
  error instanceof ApiRequestError ? error.message : fallback
const loadVersionList = async () => {
  const data = await versionApi.list(projectId.value)
  versions.value = data.items
  return data.items
}
const loadCurrent = async (versionId: string) => {
  const sequence = ++loadSequence
  loading.value = true
  loadError.value = ''
  try {
    const [detail, taskList] = await Promise.all([
      versionApi.detail(projectId.value, versionId),
      taskApi.list(projectId.value, {
        version_id: versionId,
        keyword: keyword.value.trim() || undefined,
        status: status.value,
      }),
    ])
    if (sequence !== loadSequence) return
    currentVersion.value = detail
    tasks.value = taskList.items
    total.value = taskList.total
  } catch (error) {
    if (sequence !== loadSequence) return
    loadError.value = describeError(error, '版本排期加载失败')
  } finally {
    if (sequence === loadSequence) loading.value = false
  }
}
const initialize = async () => {
  const sequence = ++loadSequence
  loading.value = true
  loadError.value = ''
  try {
    if (!access.project.value || access.project.value.id !== projectId.value) {
      await access.loadProjectAccess(projectId.value)
    }
    const items = await loadVersionList()
    if (sequence !== loadSequence) return
    if (!items.length) {
      currentVersion.value = null
      tasks.value = []
      total.value = 0
      if (routeVersionId.value) await router.replace({ name: 'project-versions', params: { projectId: projectId.value } })
      return
    }
    const selectedId = items.some((item) => item.id === routeVersionId.value)
      ? routeVersionId.value
      : items[0].id
    if (routeVersionId.value !== selectedId || route.name !== 'project-version-list') {
      await router.replace({ name: 'project-version-list', params: { projectId: projectId.value, versionId: selectedId } })
      return
    }
    await loadCurrent(selectedId)
  } catch (error) {
    if (sequence === loadSequence) loadError.value = describeError(error, '版本排期加载失败')
  } finally {
    if (sequence === loadSequence) loading.value = false
  }
}
const loadTasks = async () => {
  if (!currentVersion.value) return
  const sequence = ++loadSequence
  loading.value = true
  try {
    const data = await taskApi.list(projectId.value, {
      version_id: currentVersion.value.id,
      keyword: keyword.value.trim() || undefined,
      status: status.value,
    })
    if (sequence === loadSequence) {
      tasks.value = data.items
      total.value = data.total
    }
  } catch (error) {
    if (sequence === loadSequence) loadError.value = describeError(error, '版本任务加载失败')
  } finally {
    if (sequence === loadSequence) loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout> | undefined
const delayedSearch = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void loadTasks(), 300)
}
const switchVersion = (versionId: string) => {
  if (!versionId || versionId === currentVersion.value?.id) return
  void router.push({ name: 'project-version-list', params: { projectId: projectId.value, versionId } })
}
const openCreateVersion = () => {
  if (access.readOnly.value) return
  editingVersion.value = null
  versionDialogVisible.value = true
}
const openEditVersion = () => {
  if (!currentVersion.value || access.readOnly.value) return
  editingVersion.value = currentVersion.value
  versionDialogVisible.value = true
}
const afterVersionSaved = async (saved: ProjectVersion) => {
  await loadVersionList()
  if (routeVersionId.value !== saved.id) {
    await router.replace({ name: 'project-version-list', params: { projectId: projectId.value, versionId: saved.id } })
  } else {
    await loadCurrent(saved.id)
  }
}
const openCreateTask = (assigneeId: string) => {
  if (!currentVersion.value || access.readOnly.value) return
  selectedTask.value = null
  initialAssigneeId.value = assigneeId
  taskDialogVisible.value = true
}
const openTask = (task: Task) => {
  selectedTask.value = task
  initialAssigneeId.value = ''
  taskDialogVisible.value = true
}
const afterTaskChanged = async () => {
  if (!currentVersion.value) return
  await Promise.all([loadVersionList(), loadCurrent(currentVersion.value.id)])
}
const handleVersionWriteError = async (error: unknown) => {
  if (error instanceof ApiRequestError && (error.code === 'VERSION_REVISION_CONFLICT' || error.code?.includes('REVISION_CONFLICT'))) {
    ElMessage.warning('版本已被其他人更新，已加载最新内容')
    if (currentVersion.value) await Promise.all([loadVersionList(), loadCurrent(currentVersion.value.id)])
  } else if (error instanceof ApiRequestError && error.code === 'PROJECT_ARCHIVED') {
    ElMessage.error('项目已归档，仅支持查看版本')
  } else {
    ElMessage.error(describeError(error, '版本操作失败'))
  }
}
const requestStatusChange = async (nextStatus: VersionStatus) => {
  if (!currentVersion.value || access.readOnly.value || statusUpdating.value || nextStatus === currentVersion.value.status) return
  if (nextStatus === 'COMPLETED') {
    completionLoading.value = true
    try {
      completionImpact.value = await versionApi.completionImpact(projectId.value, currentVersion.value.id)
      completionVisible.value = true
    } catch (error) {
      await handleVersionWriteError(error)
    } finally {
      completionLoading.value = false
    }
    return
  }
  statusUpdating.value = true
  try {
    const updated = await versionApi.update(projectId.value, currentVersion.value.id, {
      expected_revision: currentVersion.value.revision,
      status: nextStatus,
    })
    currentVersion.value = updated
    await loadVersionList()
    ElMessage.success('版本状态已更新')
  } catch (error) {
    await handleVersionWriteError(error)
  } finally {
    statusUpdating.value = false
  }
}
const confirmComplete = async () => {
  if (!currentVersion.value) return
  statusUpdating.value = true
  try {
    const updated = await versionApi.update(projectId.value, currentVersion.value.id, {
      expected_revision: currentVersion.value.revision,
      status: 'COMPLETED',
    })
    currentVersion.value = updated
    completionVisible.value = false
    await loadVersionList()
    ElMessage.success('版本已完成，任务状态保持不变')
  } catch (error) {
    completionVisible.value = false
    await handleVersionWriteError(error)
  } finally {
    statusUpdating.value = false
  }
}
const confirmDelete = async () => {
  if (!currentVersion.value || access.readOnly.value) return
  deleting.value = true
  try {
    const result = await versionApi.delete(projectId.value, currentVersion.value.id, currentVersion.value.revision)
    deleteVisible.value = false
    await loadVersionList()
    ElMessage.success(`版本已删除，${result.unlinked_task_count} 条任务已解除版本关联`)
    if (result.next_version_id) {
      await router.replace({ name: 'project-version-list', params: { projectId: projectId.value, versionId: result.next_version_id } })
    } else {
      currentVersion.value = null
      tasks.value = []
      total.value = 0
      await router.replace({ name: 'project-versions', params: { projectId: projectId.value } })
    }
  } catch (error) {
    deleteVisible.value = false
    await handleVersionWriteError(error)
  } finally {
    deleting.value = false
  }
}

watch([projectId, routeVersionId], () => void initialize(), { immediate: true })
watch(status, () => void loadTasks())
onBeforeUnmount(() => clearTimeout(searchTimer))
</script>

<template>
  <main class="page version-scheduling-page">
    <el-alert
      v-if="access.readOnly.value"
      title="项目已归档或当前账号不是项目成员，仅支持查看版本排期"
      type="warning"
      show-icon
      :closable="false"
      class="readonly-alert"
    />

    <div v-if="loading && !currentVersion && !loadError" v-loading="true" class="version-page-loading" />
    <section v-else-if="loadError" class="version-error-state">
      <el-result icon="error" title="版本排期加载失败" :sub-title="loadError">
        <template #extra><el-button type="primary" @click="initialize">重新加载</el-button></template>
      </el-result>
    </section>
    <section v-else-if="!currentVersion" class="version-empty-state">
      <span class="version-empty-icon"><el-icon><Calendar /></el-icon></span>
      <p>{{ projectName }}</p>
      <h1>还没有版本排期</h1>
      <small>创建第一个版本，设置周期和参与人员后即可开始安排任务。</small>
      <el-button type="primary" :icon="Plus" :disabled="access.readOnly.value || !projectMembers.length" @click="openCreateVersion">
        创建第一个版本
      </el-button>
    </section>
    <template v-else>
      <nav class="version-view-tabs" aria-label="版本排期视图">
        <RouterLink :to="{ name: 'project-version-list', params: { projectId, versionId: currentVersion.id } }" class="active">排期列表</RouterLink>
        <RouterLink :to="{ name: 'project-version-gantt', params: { projectId, versionId: currentVersion.id }, query: ganttQuery }">甘特图</RouterLink>
      </nav>

      <section class="version-summary-bar">
        <span class="version-summary-label">当前版本</span>
        <el-select :model-value="currentVersion.id" class="version-selector" aria-label="切换版本" @change="switchVersion">
          <el-option v-for="version in versions" :key="version.id" :label="version.name" :value="version.id" />
        </el-select>
        <el-dropdown :disabled="access.readOnly.value || statusUpdating || completionLoading" trigger="click" @command="requestStatusChange">
          <button type="button" class="version-status-button" :class="currentStatus?.className" :disabled="access.readOnly.value || statusUpdating || completionLoading">
            {{ currentStatus?.label }}<span>⌄</span>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="NOT_STARTED" :disabled="currentVersion.status === 'NOT_STARTED'">未开始</el-dropdown-item>
              <el-dropdown-item command="IN_PROGRESS" :disabled="currentVersion.status === 'IN_PROGRESS'">进行中</el-dropdown-item>
              <el-dropdown-item command="COMPLETED" :disabled="currentVersion.status === 'COMPLETED'">已完成</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <span class="version-date-range">{{ currentVersion.start_date }}<em>—</em>{{ currentVersion.end_date }}</span>
        <span class="version-participant-count"><el-icon><User /></el-icon>{{ currentVersion.participants.length }} 人参与</span>
        <div class="version-summary-actions">
          <el-button :icon="EditPen" :disabled="access.readOnly.value" @click="openEditVersion">编辑版本</el-button>
          <el-button type="danger" plain :disabled="access.readOnly.value" @click="deleteVisible = true">删除版本</el-button>
          <el-button type="primary" :icon="Plus" :disabled="access.readOnly.value" @click="openCreateVersion">创建新版本</el-button>
        </div>
      </section>

      <div class="version-filter-bar">
        <el-input v-model="keyword" :prefix-icon="Search" clearable maxlength="100" placeholder="搜索版本任务" @input="delayedSearch" @clear="loadTasks" />
        <el-select v-model="status" aria-label="筛选版本任务状态">
          <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
        <span>当前筛选共 {{ total }} 条任务</span>
      </div>

      <div v-loading="loading" class="version-schedule-list">
        <section v-for="participant in currentVersion.participants" :key="participant.user_id" class="version-schedule-card">
          <header class="version-participant-panel">
            <span class="version-member-avatar large">{{ participant.name.slice(0, 1) }}</span>
            <div><strong>{{ participant.name }}</strong><small v-if="participant.department_name">{{ participant.department_name }}</small><em>{{ groupedTasks.get(participant.user_id)?.length || 0 }} 个任务</em></div>
          </header>
          <div class="version-task-table-wrap">
            <table v-if="groupedTasks.get(participant.user_id)?.length" class="version-task-table">
              <thead><tr><th>任务名称</th><th>任务状态</th><th>开始时间</th><th>结束时间</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="task in groupedTasks.get(participant.user_id)" :key="task.id">
                  <td><button type="button" @click="openTask(task)">{{ task.name }}</button></td>
                  <td><span class="version-task-status" :class="taskStatusMeta[task.status].className">{{ taskStatusMeta[task.status].label }}</span></td>
                  <td>{{ task.start_date || '—' }}</td><td>{{ task.due_date || '—' }}</td>
                  <td><el-button link type="primary" @click="openTask(task)">{{ access.readOnly.value ? '查看' : '编辑' }}</el-button></td>
                </tr>
              </tbody>
            </table>
            <button v-else type="button" class="version-add-task-empty" :disabled="access.readOnly.value" @click="openCreateTask(participant.user_id)">
              <el-icon><Plus /></el-icon><span>添加任务</span><small v-if="keyword || status !== 'ALL'">当前筛选下暂无任务</small>
            </button>
            <el-button v-if="groupedTasks.get(participant.user_id)?.length" class="version-row-add" link :icon="Plus" :disabled="access.readOnly.value" @click="openCreateTask(participant.user_id)">添加任务</el-button>
          </div>
        </section>
      </div>
    </template>

    <VersionDialog v-model="versionDialogVisible" :project-id="projectId" :members="projectMembers" :version="editingVersion" :read-only="access.readOnly.value" @saved="afterVersionSaved" />
    <TaskDialog v-model="taskDialogVisible" :project-id="projectId" :members="projectMembers" :versions="versions" :task="selectedTask" :initial-assignee-id="initialAssigneeId" :initial-version-id="currentVersion?.id" :read-only="access.readOnly.value" @changed="afterTaskChanged" />

    <el-dialog v-model="completionVisible" width="505px" class="product-dialog version-confirm-dialog" :close-on-click-modal="false">
      <div class="version-confirm-content"><span class="version-confirm-icon complete">✓</span><div><h3>完成版本</h3><p>当前版本共有 {{ completionImpact?.task_count || 0 }} 条任务，其中 <strong>{{ completionImpact?.unfinished_task_count || 0 }}</strong> 条尚未完成。</p><small>确认后只修改版本状态，不会改变任何任务状态。</small></div></div>
      <template #footer><el-button @click="completionVisible = false">取消</el-button><el-button type="primary" :loading="statusUpdating" @click="confirmComplete">确认完成</el-button></template>
    </el-dialog>
    <el-dialog v-model="deleteVisible" width="505px" class="product-dialog version-confirm-dialog" :close-on-click-modal="false">
      <div class="version-confirm-content"><span class="version-confirm-icon danger">!</span><div><h3>删除版本</h3><p>当前版本关联 {{ currentVersion?.task_count || 0 }} 条任务。删除版本后，任务不会删除，只会解除版本关联并继续保留在团队任务中。</p></div></div>
      <template #footer><el-button @click="deleteVisible = false">取消</el-button><el-button type="danger" :loading="deleting" @click="confirmDelete">确认删除</el-button></template>
    </el-dialog>
  </main>
</template>
