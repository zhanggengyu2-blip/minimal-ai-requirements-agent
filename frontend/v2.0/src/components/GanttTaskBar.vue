<script setup lang="ts">
import type { Task } from '../api'

defineProps<{
  task: Task
  left: number
  width: number
  durationDays: number
}>()
const emit = defineEmits<{ open: [task: Task] }>()
</script>

<template>
  <button
    type="button"
    class="gantt-task-bar"
    :style="{ left: `${left}px`, width: `${width}px` }"
    :title="`${task.name}：${task.start_date} 至 ${task.due_date}`"
    @click="emit('open', task)"
  >{{ durationDays }} 天</button>
</template>
