<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import type { Task, TaskPriority, TaskStatus } from '../api'
import {
  buildGanttRange,
  buildHeaderBands,
  businessToday,
  dateAtScrollCenter,
  dateToOrdinal,
  ganttBarGeometry,
  scaleDayWidth,
  scrollLeftForDate,
  type GanttHeaderBand,
  type GanttScale,
} from '../utils/gantt'
import GanttTaskBar from './GanttTaskBar.vue'

export interface GanttMember {
  user_id: string
  name: string
  department_name?: string | null
}

const LEFT_WIDTH = 455
const props = withDefaults(defineProps<{
  members: ReadonlyArray<GanttMember>
  tasks: ReadonlyArray<Task>
  versionNames?: ReadonlyMap<string, string>
  scale: GanttScale
  referenceStart?: string
  referenceEnd?: string
  loading?: boolean
}>(), { versionNames: () => new Map(), referenceStart: '', referenceEnd: '', loading: false })
const emit = defineEmits<{
  'update:scale': [scale: GanttScale]
  open: [task: Task]
}>()

const scrollRef = ref<HTMLElement>()
const collapsedIds = ref<Set<string>>(new Set())
const today = businessToday()
const dayWidth = computed(() => scaleDayWidth[props.scale])
const range = computed(() => buildGanttRange([
  ...props.tasks.flatMap((task) => [task.start_date, task.due_date]),
  props.referenceStart,
  props.referenceEnd,
], today))
const bands = computed(() => buildHeaderBands(range.value, props.scale))
const timelineWidth = computed(() => range.value.dayCount * dayWidth.value)
const todayX = computed(() => (dateToOrdinal(today) - dateToOrdinal(range.value.start) + 0.5) * dayWidth.value)
const tasksByMember = computed(() => {
  const groups = new Map<string, Task[]>()
  props.members.forEach((member) => groups.set(member.user_id, []))
  props.tasks.forEach((task) => groups.get(task.assignee_id)?.push(task))
  return groups
})
const rows = computed(() => props.members.flatMap((member) => {
  const memberTasks = tasksByMember.value.get(member.user_id) || []
  return [
    { type: 'group' as const, key: `group-${member.user_id}`, member, taskCount: memberTasks.length },
    ...(collapsedIds.value.has(member.user_id)
      ? []
      : memberTasks.map((task) => ({ type: 'task' as const, key: task.id, member, task }))),
  ]
}))

const taskStatusMeta: Record<TaskStatus, { label: string; className: string }> = {
  NOT_STARTED: { label: '未开始', className: 'not-started' },
  IN_PROGRESS: { label: '进行中', className: 'in-progress' },
  COMPLETED: { label: '已完成', className: 'completed' },
  CANCELED: { label: '已取消', className: 'canceled' },
}
const priorityMeta: Record<TaskPriority, { label: string; className: string }> = {
  P0: { label: 'P0 · 重要紧急', className: 'p0' },
  P1: { label: 'P1 · 重要不紧急', className: 'p1' },
  P2: { label: 'P2 · 紧急不重要', className: 'p2' },
  P3: { label: 'P3 · 不重要不紧急', className: 'p3' },
}
const bandStyle = (band: GanttHeaderBand) => ({
  left: `${band.startIndex * dayWidth.value}px`,
  width: `${band.dayCount * dayWidth.value}px`,
})
const barFor = (task: Task) => ganttBarGeometry(task.start_date, task.due_date, range.value.start, dayWidth.value)
const toggleMember = (userId: string) => {
  const next = new Set(collapsedIds.value)
  if (next.has(userId)) next.delete(userId)
  else next.add(userId)
  collapsedIds.value = next
}
const viewportWidth = () => Math.max(240, (scrollRef.value?.clientWidth || 900) - LEFT_WIDTH)
const centerDate = (date: string) => {
  if (!scrollRef.value) return
  scrollRef.value.scrollLeft = scrollLeftForDate(date, range.value.start, dayWidth.value, viewportWidth())
}
const goToday = () => centerDate(today)
const moveWindow = (direction: -1 | 1) => {
  if (!scrollRef.value) return
  scrollRef.value.scrollBy({ left: direction * viewportWidth(), behavior: 'smooth' })
}
const changeScale = async (scale: GanttScale) => {
  if (scale === props.scale) return
  const centeredDate = scrollRef.value
    ? dateAtScrollCenter(scrollRef.value.scrollLeft, viewportWidth(), range.value.start, dayWidth.value)
    : today
  emit('update:scale', scale)
  await nextTick()
  centerDate(centeredDate)
}

watch(() => props.members.map((member) => member.user_id).join(','), () => {
  const validIds = new Set(props.members.map((member) => member.user_id))
  collapsedIds.value = new Set([...collapsedIds.value].filter((id) => validIds.has(id)))
})
onMounted(() => void nextTick(goToday))
</script>

<template>
  <section v-loading="loading" class="gantt-shell">
    <div ref="scrollRef" class="gantt-scroll" data-testid="gantt-scroll">
      <div class="gantt-grid" :style="{ width: `${LEFT_WIDTH + timelineWidth}px`, '--gantt-left-width': `${LEFT_WIDTH}px` }">
        <header class="gantt-left-header">
          <span>任务名称</span><span>版本</span><span>优先级</span><span>进度</span>
        </header>
        <header class="gantt-time-header" :style="{ width: `${timelineWidth}px` }">
          <div class="gantt-time-actions">
            <div class="gantt-scale-switch" aria-label="甘特图刻度">
              <button type="button" :class="{ active: scale === 'day' }" @click="changeScale('day')">日</button>
              <button type="button" :class="{ active: scale === 'week' }" @click="changeScale('week')">周</button>
              <button type="button" :class="{ active: scale === 'month' }" @click="changeScale('month')">月</button>
            </div>
            <button type="button" class="gantt-today-button" @click="goToday">今天</button>
            <el-button-group>
              <el-button :icon="ArrowLeft" aria-label="向前移动一个窗口" @click="moveWindow(-1)" />
              <el-button :icon="ArrowRight" aria-label="向后移动一个窗口" @click="moveWindow(1)" />
            </el-button-group>
          </div>
          <div class="gantt-header-bands primary">
            <span v-for="band in bands.primary" :key="band.key" :style="bandStyle(band)">{{ band.label }}</span>
          </div>
          <div class="gantt-header-bands secondary">
            <span v-for="band in bands.secondary" :key="band.key" :style="bandStyle(band)">{{ band.label }}</span>
          </div>
          <span class="gantt-today-marker" :style="{ left: `${todayX}px` }">今天</span>
        </header>

        <template v-for="row in rows" :key="row.key">
          <div v-if="row.type === 'group'" class="gantt-left-row group-row">
            <button type="button" class="gantt-member-toggle" @click="toggleMember(row.member.user_id)">
              <span>{{ collapsedIds.has(row.member.user_id) ? '›' : '⌄' }}</span>
              <em>{{ row.member.name.slice(0, 1) }}</em>
              <strong>{{ row.member.name }}</strong>
              <small v-if="row.member.department_name">{{ row.member.department_name }}</small>
              <b>{{ row.taskCount }} 个任务</b>
            </button>
          </div>
          <div v-else class="gantt-left-row task-row">
            <button type="button" class="gantt-task-name" @click="emit('open', row.task)">{{ row.task.name }}</button>
            <span class="gantt-task-version">{{ row.task.version_id ? (versionNames.get(row.task.version_id) || '已关联版本') : '未排版本' }}</span>
            <span class="gantt-priority" :class="priorityMeta[row.task.priority].className">{{ priorityMeta[row.task.priority].label }}</span>
            <span class="gantt-progress" :class="taskStatusMeta[row.task.status].className">{{ taskStatusMeta[row.task.status].label }}</span>
          </div>

          <div
            class="gantt-timeline-row"
            :class="row.type === 'group' ? 'group-row' : 'task-row'"
            :style="{ width: `${timelineWidth}px`, '--gantt-day-width': `${dayWidth}px` }"
          >
            <span class="gantt-today-line" :style="{ left: `${todayX}px` }" />
            <GanttTaskBar
              v-if="row.type === 'task' && barFor(row.task)"
              :task="row.task"
              :left="barFor(row.task)!.left"
              :width="barFor(row.task)!.width"
              :duration-days="barFor(row.task)!.durationDays"
              @open="emit('open', $event)"
            />
          </div>
        </template>
      </div>
    </div>
  </section>
</template>
