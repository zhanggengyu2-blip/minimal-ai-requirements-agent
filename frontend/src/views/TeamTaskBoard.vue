<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Search, User } from '@element-plus/icons-vue'
import TaskCard from '../components/TaskCard.vue'
import TaskDialog from '../components/TaskDialog.vue'
import {
  taskApi,
  versionApi,
  type ProjectMember,
  type Task,
  type TaskStatusFilter,
  type VersionSummary,
} from '../api'
import { ApiRequestError } from '../api/http'
import { useProjectAccess } from '../composables/useProjectAccess'
import { useTeamTaskModuleState } from '../composables/useTaskModuleState'
import { mergeVisibleTaskOrder, reorderVisibleIds } from '../utils/taskBoard'

const route = useRoute()
const access = useProjectAccess()
const moduleState = useTeamTaskModuleState()
const projectId = computed(() => String(route.params.projectId || ''))
const projectName = computed(() => access.project.value?.name || '当前项目')
const members = computed(() => access.members.value?.items || [])
const loading = ref(false)
const tasks = ref<Task[]>([])
const versions = ref<VersionSummary[]>([])
const total = ref(0)
const { keyword, status } = moduleState
const dialogVisible = ref(false)
const selectedTask = ref<Task | null>(null)
const initialAssigneeId = ref('')
const draggingTask = ref<Task | null>(null)
const sortingAssigneeIds = ref<Set<string>>(new Set())
let loadSequence = 0

const statusOptions: Array<{ label: string; value: TaskStatusFilter }> = [
  { label: '未完成任务', value: 'UNFINISHED' },
  { label: '全部状态', value: 'ALL' },
  { label: '未开始', value: 'NOT_STARTED' },
  { label: '进行中', value: 'IN_PROGRESS' },
  { label: '已完成', value: 'COMPLETED' },
  { label: '已取消', value: 'CANCELED' },
]
const groupedTasks = computed(() => {
  const result = new Map<string, Task[]>()
  members.value.forEach((member) => result.set(member.user_id, []))
  tasks.value.forEach((task) => result.get(task.assignee_id)?.push(task))
  return result
})
const versionNames = computed(() => new Map(versions.value.map((version) => [version.id, version.name])))

const load = async () => {
  if (!projectId.value) return
  const sequence = ++loadSequence
  loading.value = true
  try {
    const data = await taskApi.list(projectId.value, {
      keyword: keyword.value.trim() || undefined,
      status: status.value,
    })
    if (sequence === loadSequence) {
      tasks.value = data.items
      total.value = data.total
    }
  } finally {
    if (sequence === loadSequence) loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout> | undefined
const delayedSearch = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void load(), 300)
}
const openCreate = (assigneeId = '') => {
  if (access.readOnly.value) return
  selectedTask.value = null
  initialAssigneeId.value = assigneeId
  dialogVisible.value = true
}
const openTask = (task: Task) => {
  selectedTask.value = task
  initialAssigneeId.value = ''
  dialogVisible.value = true
}

const setLocalLaneOrder = (assigneeId: string, orderedIds: string[]) => {
  const next = [...tasks.value]
  const positions = next
    .map((task, index) => task.assignee_id === assigneeId ? index : -1)
    .filter((index) => index >= 0)
  const laneMap = new Map(next.filter((task) => task.assignee_id === assigneeId).map((task) => [task.id, task]))
  positions.forEach((position, index) => {
    const replacement = laneMap.get(orderedIds[index])
    if (replacement) next[position] = replacement
  })
  tasks.value = next
}
const markSorting = (assigneeId: string, busy: boolean) => {
  const next = new Set(sortingAssigneeIds.value)
  if (busy) next.add(assigneeId)
  else next.delete(assigneeId)
  sortingAssigneeIds.value = next
}
const startDrag = (task: Task) => {
  draggingTask.value = task
}
const finishDrag = () => {
  draggingTask.value = null
}
const dropOn = async (member: ProjectMember, target: Task) => {
  const dragged = draggingTask.value
  draggingTask.value = null
  if (
    !dragged
    || access.readOnly.value
    || dragged.assignee_id !== member.user_id
    || target.assignee_id !== member.user_id
    || dragged.id === target.id
    || sortingAssigneeIds.value.has(member.user_id)
  ) return

  const oldTasks = [...tasks.value]
  const visibleIds = (groupedTasks.value.get(member.user_id) || []).map((task) => task.id)
  const orderedVisibleIds = reorderVisibleIds(visibleIds, dragged.id, target.id)
  setLocalLaneOrder(member.user_id, orderedVisibleIds)
  markSorting(member.user_id, true)
  try {
    const fullLane = await taskApi.getLaneOrder(projectId.value, member.user_id)
    const completeOrder = mergeVisibleTaskOrder(fullLane.ordered_task_ids, orderedVisibleIds)
    await taskApi.reorderLane(projectId.value, member.user_id, {
      expected_lane_revision: fullLane.lane_revision,
      ordered_task_ids: completeOrder,
    })
    await load()
  } catch (error) {
    tasks.value = oldTasks
    if (error instanceof ApiRequestError && (
      error.code === 'LANE_REVISION_CONFLICT'
      || error.code === 'TASK_LANE_ORDER_INVALID'
      || error.code?.includes('REVISION_CONFLICT')
    )) {
      ElMessage.warning('任务顺序已被其他人更新，已恢复最新顺序')
    } else if (error instanceof ApiRequestError) {
      ElMessage.error(error.message)
    }
    await load().catch(() => undefined)
  } finally {
    markSorting(member.user_id, false)
  }
}

const initialize = async () => {
  moduleState.ensureProject(projectId.value)
  if (!access.project.value || access.project.value.id !== projectId.value) {
    await access.loadProjectAccess(projectId.value)
  }
  const [versionList] = await Promise.all([
    versionApi.list(projectId.value).catch(() => ({ items: [], total: 0 })),
    load(),
  ])
  versions.value = versionList.items
}

watch(projectId, () => void initialize())
watch(status, () => void load())
const openLinkedTask = async () => {
  const id = route.query?.task_id
  if (typeof id === 'string' && projectId.value) {
    try { openTask(await taskApi.detail(projectId.value, id)) } catch { /* API displays permission errors. */ }
  }
}
watch(() => route.query?.task_id, () => void openLinkedTask())
onMounted(async () => { await initialize(); await openLinkedTask() })
onBeforeUnmount(() => clearTimeout(searchTimer))
onBeforeRouteLeave((to) => {
  const staysInModule = ['project-task-board', 'project-task-gantt'].includes(String(to.name || ''))
    && String(to.params.projectId || '') === projectId.value
  if (!staysInModule) moduleState.reset()
})
</script>

<template>
  <main class="page team-task-page">
    <el-alert
      v-if="access.readOnly.value"
      title="项目已归档或当前账号不是项目成员，仅支持查看任务"
      type="warning"
      show-icon
      :closable="false"
      class="readonly-alert"
    />

    <div class="team-task-heading">
      <div class="breadcrumb-title team-task-breadcrumb">
        <strong>{{ projectName }}</strong><span>/</span><strong>团队任务</strong>
      </div>
      <span class="team-task-total">当前筛选共 {{ total }} 条任务</span>
    </div>

    <div class="team-task-toolbar">
      <nav class="task-view-tabs" aria-label="团队任务视图">
        <RouterLink :to="{ name: 'project-task-board', params: { projectId } }" class="active">任务面板</RouterLink>
        <RouterLink :to="{ name: 'project-task-gantt', params: { projectId } }">甘特图</RouterLink>
      </nav>
      <el-input
        v-model="keyword"
        :prefix-icon="Search"
        maxlength="100"
        clearable
        placeholder="搜索任务名称"
        class="task-search"
        @input="delayedSearch"
        @clear="load"
      />
      <el-select v-model="status" class="task-status-filter" aria-label="筛选任务状态">
        <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
      </el-select>
      <el-button type="primary" :icon="Plus" :disabled="access.readOnly.value || !members.length" @click="openCreate()">
        新建任务
      </el-button>
    </div>

    <div v-loading="loading" class="task-lanes-wrap">
      <section
        v-for="member in members"
        :key="member.user_id"
        class="task-lane"
        :class="{ 'lane-sorting': sortingAssigneeIds.has(member.user_id) }"
      >
        <header class="task-lane-header">
          <span class="task-member-avatar">{{ member.name.slice(0, 1) }}</span>
          <div><strong>{{ member.name }}</strong><small>{{ member.department_name }}</small></div>
          <em>{{ groupedTasks.get(member.user_id)?.length || 0 }}</em>
        </header>

        <div class="task-lane-content">
          <TaskCard
            v-for="task in groupedTasks.get(member.user_id) || []"
            :key="task.id"
            :task="task"
            :version-name="task.version_id ? versionNames.get(task.version_id) : ''"
            :read-only="access.readOnly.value || sortingAssigneeIds.has(member.user_id)"
            @open="openTask"
            @dragstart="startDrag"
            @dragend="finishDrag"
            @dragover.prevent
            @drop.prevent="dropOn(member, task)"
          />
          <div v-if="!groupedTasks.get(member.user_id)?.length" class="task-lane-empty">
            <el-icon :size="25"><User /></el-icon>
            <span>暂无符合条件的任务</span>
          </div>
        </div>
        <el-button
          class="task-lane-add"
          :icon="Plus"
          :disabled="access.readOnly.value"
          @click="openCreate(member.user_id)"
        >新建任务</el-button>
      </section>

      <el-empty v-if="!loading && !members.length" description="项目暂无成员，请先在项目管理中添加成员" />
    </div>

    <TaskDialog
      v-model="dialogVisible"
      :project-id="projectId"
      :members="members"
      :task="selectedTask"
      :versions="versions"
      :initial-assignee-id="initialAssigneeId"
      :read-only="access.readOnly.value"
      @changed="load"
    />
  </main>
</template>
