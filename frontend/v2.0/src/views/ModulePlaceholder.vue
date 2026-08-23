<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Calendar, Lock, Operation } from '@element-plus/icons-vue'
import { useProjectAccess } from '../composables/useProjectAccess'

const route = useRoute()
const access = useProjectAccess()
const title = computed(() => route.meta.placeholderTitle || '模块建设中')
const description = computed(() => route.meta.placeholderDescription || '该模块将在后续任务包中实现。')
const isTaskModule = computed(() => String(route.name || '').includes('task'))
</script>

<template>
  <main class="page module-placeholder-page">
    <el-alert
      v-if="access.project.value?.status === 'ARCHIVED'"
      title="项目已归档，仅支持查看"
      type="warning"
      show-icon
      :closable="false"
    />
    <section class="module-placeholder-card">
      <span class="placeholder-icon"><el-icon><Operation v-if="isTaskModule" /><Calendar v-else /></el-icon></span>
      <p class="placeholder-project">{{ access.project.value?.name }}</p>
      <h1>{{ title }}</h1>
      <p>{{ description }}</p>
      <div class="placeholder-status"><el-icon><Lock /></el-icon> 路由、项目可见性与只读上下文已接入</div>
      <div v-if="isTaskModule" class="placeholder-actions">
        <RouterLink :to="{ name: 'project-task-board', params: { projectId: route.params.projectId } }">任务面板</RouterLink>
        <RouterLink :to="{ name: 'project-task-gantt', params: { projectId: route.params.projectId } }">甘特图</RouterLink>
      </div>
    </section>
  </main>
</template>
