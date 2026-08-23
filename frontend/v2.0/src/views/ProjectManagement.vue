<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { FolderOpened, Plus, Refresh, User } from '@element-plus/icons-vue'
import type { Project, ProjectStatus } from '../api'
import { projectApi } from '../api'
import { ApiRequestError } from '../api/http'
import { PROJECT_STATUS, formatDate } from '../constants'
import ProjectMemberDialog from '../components/ProjectMemberDialog.vue'

const emit = defineEmits<{ create: []; changed: [] }>()
const loading = ref(false)
const actionProjectId = ref('')
const rows = ref<Project[]>([])
const total = ref(0)
const query = reactive<{ page: number; page_size: number; status?: ProjectStatus }>({
  page: 1,
  page_size: 10,
  status: undefined,
})
const router = useRouter()
const memberDialog = ref(false)
const memberProject = ref<Project | null>(null)

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
const viewProject = (project: Project) => router.push({
  name: 'project-requirements',
  params: { projectId: project.id },
})
const openMembers = (project: Project) => {
  memberProject.value = project
  memberDialog.value = true
}
const changeStatus = async (project: Project) => {
  const archive = project.status === 'ACTIVE'
  await ElMessageBox.confirm(
    archive
      ? `归档“${project.name}”后，项目内容仍可查看，但所有写操作将被禁用。`
      : `确认重新打开“${project.name}”吗？`,
    archive ? '归档项目' : '重新打开项目',
    {
      type: archive ? 'warning' : 'info',
      confirmButtonText: archive ? '确认归档' : '确认打开',
      cancelButtonText: '取消',
    },
  )
  actionProjectId.value = project.id
  try {
    await projectApi.update(project.id, {
      expected_revision: project.revision,
      status: archive ? 'ARCHIVED' : 'ACTIVE',
    })
    ElMessage.success(archive ? '项目已归档' : '项目已重新打开')
    await refresh()
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 409) {
      ElMessage.warning('项目已被其他人修改，请刷新后重试')
      await refresh()
    }
  } finally {
    actionProjectId.value = ''
  }
}
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
        <el-table-column label="操作" width="245" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewProject(row)">查看</el-button>
            <el-button link type="primary" :icon="User" @click="openMembers(row)">成员</el-button>
            <el-button
              link
              :type="row.status === 'ACTIVE' ? 'danger' : 'success'"
              :loading="actionProjectId === row.id"
              @click="changeStatus(row)"
            >
              {{ row.status === 'ACTIVE' ? '归档' : '重新打开' }}
            </el-button>
          </template>
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
    <ProjectMemberDialog
      v-model="memberDialog"
      :project="memberProject"
      @saved="refresh"
    />
  </main>
</template>
