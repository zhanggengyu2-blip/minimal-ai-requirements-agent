<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, MagicStick, Plus, Tickets } from '@element-plus/icons-vue'
import type {
  AnalysisStatus,
  Project,
  Requirement,
  RequirementPriority,
} from '../api'
import { requirementApi } from '../api'
import { ANALYSIS_STATUS, REQUIREMENT_TYPE, shortId } from '../constants'

const props = defineProps<{ projects: Project[]; selectedProjectId?: string }>()
const emit = defineEmits<{ create: []; detail: [id: string] }>()
const loading = ref(false)
const batchLoading = ref(false)
const items = ref<Requirement[]>([])
const total = ref(0)
const selectedIds = ref<string[]>([])
const query = reactive<{
  project_id?: string
  page: number
  page_size: number
  keyword?: string
}>({ page: 1, page_size: 20 })

const columns: Array<{ key: RequirementPriority | 'UNSET'; title: string; color: string }> = [
  { key: 'P0', title: '紧急', color: '#e42b2b' },
  { key: 'P1', title: '高优先级', color: '#f27a12' },
  { key: 'P2', title: '中优先级', color: '#1969f5' },
  { key: 'P3', title: '低优先级', color: '#667085' },
  { key: 'UNSET', title: '待分析', color: '#9a67ea' },
]
const grouped = computed(() =>
  Object.fromEntries(columns.map((column) => [
    column.key,
    items.value.filter((item) => (item.priority || 'UNSET') === column.key),
  ])),
)
const currentProjectName = computed(() =>
  props.projects.find((project) => project.id === query.project_id)?.name || '全部项目',
)

const load = async () => {
  loading.value = true
  try {
    const data = await requirementApi.list(query)
    items.value = data.items
    total.value = data.total
    selectedIds.value = selectedIds.value.filter((id) => items.value.some((item) => item.id === id))
  } finally {
    loading.value = false
  }
}
const search = () => {
  query.page = 1
  load()
}
let timer: ReturnType<typeof setTimeout> | undefined
const delayedSearch = () => {
  clearTimeout(timer)
  timer = setTimeout(search, 350)
}
const toggle = (id: string, checked: boolean) => {
  selectedIds.value = checked
    ? [...new Set([...selectedIds.value, id])]
    : selectedIds.value.filter((item) => item !== id)
}
const batchAnalyze = async () => {
  const ids = selectedIds.value.length
    ? selectedIds.value
    : items.value.filter((item) => item.analysis_status !== 'ANALYZING').map((item) => item.id)
  if (!ids.length) {
    ElMessage.warning('当前页没有可提交分析的需求')
    return
  }
  batchLoading.value = true
  try {
    const result = await requirementApi.batchAnalyze(ids.slice(0, 50))
    ElMessage.success(`批量分析提交成功，共 ${result.total} 条需求`)
    selectedIds.value = []
  } finally {
    batchLoading.value = false
  }
}
const statusType = (status: AnalysisStatus) =>
  ({ ANALYZED: 'success', FAILED: 'danger', ANALYZING: 'primary', PENDING: 'warning' } as const)[status]

watch(() => props.selectedProjectId, (id) => {
  if (id === query.project_id) return
  query.project_id = id || undefined
  search()
})
defineExpose({ refresh: load })
onMounted(load)
</script>

<template>
  <main class="page requirement-page">
    <div class="breadcrumb-title"><strong>{{ currentProjectName }}</strong><span>/</span><strong>需求</strong></div>
    <div class="requirement-toolbar">
      <el-input
        v-model="query.keyword"
        :prefix-icon="Search"
        maxlength="100"
        clearable
        placeholder="搜索需求内容"
        @input="delayedSearch"
        @clear="search"
      />
      <div class="toolbar-actions">
        <el-button :icon="MagicStick" :loading="batchLoading" @click="batchAnalyze">
          AI批量分析<span v-if="selectedIds.length">（{{ selectedIds.length }}）</span>
        </el-button>
        <el-button type="primary" :icon="Plus" @click="emit('create')">提交新需求</el-button>
      </div>
    </div>
    <p class="sort-hint">按 AI 建议优先级分组 · 点击卡片查看完整分析结果</p>

    <div v-loading="loading" class="kanban-wrap">
      <div v-for="column in columns" :key="column.key" class="kanban-column" :class="column.key.toLowerCase()">
        <div class="column-title">
          <i :style="{ background: column.color }" />
          <strong>{{ column.title }}</strong>
          <span>{{ grouped[column.key].length }}</span>
        </div>
        <div class="column-content">
          <article
            v-for="item in grouped[column.key]"
            :key="item.id"
            class="requirement-card"
            @click="emit('detail', item.id)"
          >
            <div class="card-top">
              <el-checkbox
                :model-value="selectedIds.includes(item.id)"
                @click.stop
                @change="toggle(item.id, Boolean($event))"
              />
              <span class="req-id">{{ shortId(item.id) }}</span>
              <span v-if="item.priority" :class="`priority-badge ${item.priority.toLowerCase()}`">{{ item.priority }}</span>
            </div>
            <p>{{ item.standard_content || item.raw_content }}</p>
            <div class="card-meta">
              <el-tag size="small" :type="statusType(item.analysis_status)" effect="light">
                {{ ANALYSIS_STATUS[item.analysis_status] }}
              </el-tag>
              <el-tag v-if="item.type" size="small" type="info" effect="plain">{{ REQUIREMENT_TYPE[item.type] }}</el-tag>
              <span v-if="item.is_fake" class="fake-label">伪需求</span>
            </div>
            <div v-if="item.analysis_status === 'FAILED'" class="card-error">
              需求保存成功，但AI分析失败，可稍后重试
            </div>
          </article>
          <div v-if="!grouped[column.key].length" class="column-empty">
            <el-icon :size="24"><Tickets /></el-icon><span>暂无需求</span>
          </div>
        </div>
      </div>
    </div>

    <div class="pagination-row requirement-pagination">
      <span>共 {{ total }} 条需求</span>
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="sizes, prev, pager, next"
        @change="load"
      />
    </div>
  </main>
</template>
