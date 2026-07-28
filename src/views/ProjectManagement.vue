<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { FolderOpened, Plus, Refresh } from '@element-plus/icons-vue'
import type { Project, ProjectStatus } from '../api'
import { projectApi } from '../api'
import { PROJECT_STATUS, formatDate } from '../constants'

const emit = defineEmits<{ create: []; changed: [] }>()
const loading = ref(false)
const rows = ref<Project[]>([])
const total = ref(0)
const query = reactive<{ page: number; page_size: number; status?: ProjectStatus }>({
  page: 1,
  page_size: 10,
  status: undefined,
})

const load = async () => {
  loading.value = true
  try {
    const data = await projectApi.list(query)
    rows.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}
const filter = () => {
  query.page = 1
  load()
}
const statusLabel = (status: ProjectStatus) => PROJECT_STATUS[status]
const refresh = async () => {
  await load()
  emit('changed')
}
defineExpose({ refresh })
onMounted(load)
</script>

<template>
  <main class="page project-page">
    <div class="page-title-row">
      <div>
        <h1>项目管理</h1>
        <p>创建并管理团队项目，归集每个项目下的业务需求</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="emit('create')">新建项目</el-button>
    </div>
    <section class="surface-card">
      <div class="table-toolbar">
        <el-segmented
          v-model="query.status"
          :options="[
            { label: '全部项目', value: undefined },
            { label: '正常项目', value: 'ACTIVE' },
            { label: '已归档', value: 'ARCHIVED' },
          ]"
          @change="filter"
        />
        <el-button :icon="Refresh" :loading="loading" @click="refresh">刷新</el-button>
      </div>
      <el-table v-loading="loading" :data="rows" row-key="id" class="project-table">
        <el-table-column label="项目名称" min-width="210">
          <template #default="{ row }">
            <div class="project-name">
              <span class="folder-icon"><el-icon><FolderOpened /></el-icon></span>
              <div><strong>{{ row.name }}</strong><small>{{ row.description || '暂无项目简介' }}</small></div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="125">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'" effect="light">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="requirement_count" label="需求数量" width="120" />
        <el-table-column label="项目上下文" min-width="300" show-overflow-tooltip>
          <template #default="{ row }">{{ row.project_context }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_time) }}</template>
        </el-table-column>
      </el-table>
      <div v-if="!loading && !rows.length" class="empty-state">
        <el-icon :size="40"><FolderOpened /></el-icon>
        <h3>暂无符合条件的项目</h3>
        <p>创建第一个项目后，即可开始收集需求</p>
      </div>
      <div class="pagination-row">
        <span>共 {{ total }} 个项目</span>
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="sizes, prev, pager, next"
          @change="load"
        />
      </div>
    </section>
  </main>
</template>
