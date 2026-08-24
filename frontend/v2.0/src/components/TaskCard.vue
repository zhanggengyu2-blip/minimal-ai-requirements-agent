<script setup lang="ts">
import { computed } from 'vue'
import { Calendar, Clock } from '@element-plus/icons-vue'
import type { Task, TaskPriority, TaskStatus } from '../api'

const props = withDefaults(defineProps<{
  task: Task
  readOnly?: boolean
}>(), { readOnly: false })
const emit = defineEmits<{
  open: [task: Task]
  dragstart: [task: Task, event: DragEvent]
  dragend: []
}>()

const statusMeta: Record<TaskStatus, { label: string; className: string }> = {
  NOT_STARTED: { label: '未开始', className: 'not-started' },
  IN_PROGRESS: { label: '进行中', className: 'in-progress' },
  COMPLETED: { label: '已完成', className: 'completed' },
  CANCELED: { label: '已取消', className: 'canceled' },
}
const priorityMeta: Record<TaskPriority, { label: string; className: string }> = {
  P0: { label: '重要且紧急', className: 'p0' },
  P1: { label: '重要不紧急', className: 'p1' },
  P2: { label: '紧急不重要', className: 'p2' },
  P3: { label: '不重要不紧急', className: 'p3' },
}
const status = computed(() => statusMeta[props.task.status])
const priority = computed(() => priorityMeta[props.task.priority])
const dateText = computed(() => {
  if (props.task.start_date && props.task.due_date) return `${props.task.start_date} 至 ${props.task.due_date}`
  if (props.task.due_date) return `截止 ${props.task.due_date}`
  if (props.task.start_date) return `开始 ${props.task.start_date}`
  return '未设置日期'
})

const startDrag = (event: DragEvent) => {
  event.dataTransfer?.setData('text/plain', props.task.id)
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
  emit('dragstart', props.task, event)
}
</script>

<template>
  <article
    class="task-card"
    :class="{ 'task-card-readonly': readOnly }"
    tabindex="0"
    role="button"
    :aria-label="`查看任务：${task.name}`"
    @click="emit('open', task)"
    @keydown.enter="emit('open', task)"
  >
    <div class="task-card-heading">
      <span class="task-status-dot" :class="status.className" />
      <h3>{{ task.name }}</h3>
      <button
        v-if="!readOnly"
        type="button"
        class="task-drag-handle"
        draggable="true"
        aria-label="拖动调整任务顺序"
        title="拖动调整顺序"
        @click.stop
        @dragstart.stop="startDrag"
        @dragend.stop="emit('dragend')"
      >⠿</button>
    </div>
    <p class="task-description">{{ task.description || '暂无任务说明' }}</p>
    <div class="task-card-meta">
      <span class="task-status-chip" :class="status.className">{{ status.label }}</span>
      <span class="task-priority-chip" :class="priority.className">{{ task.priority }} · {{ priority.label }}</span>
    </div>
    <div class="task-card-detail">
      <span><el-icon><Calendar /></el-icon>{{ dateText }}</span>
      <span><el-icon><Clock /></el-icon>{{ task.version_id ? '已关联版本' : '未排版本' }}</span>
    </div>
  </article>
</template>
