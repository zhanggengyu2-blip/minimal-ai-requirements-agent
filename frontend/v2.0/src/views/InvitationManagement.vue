<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { CopyDocument, InfoFilled, Plus, Search } from '@element-plus/icons-vue'
import type { Department, Invitation, InvitationStatus } from '../api'
import { invitationApi } from '../api'
import { INVITATION_STATUS, formatDate } from '../constants'

const props = defineProps<{ departments: Department[] }>()
const loading = ref(false)
const submitting = ref(false)
const rows = ref<Invitation[]>([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const form = reactive({ department_id: '', user_name: '' })
const stats = reactive<Record<InvitationStatus, number>>({ UNUSED: 0, USED: 0, DISABLED: 0 })
const query = reactive<{
  page: number
  page_size: number
  keyword?: string
  department_id?: string
  status?: InvitationStatus
}>({ page: 1, page_size: 10 })
const rules: FormRules = {
  department_id: [{ required: true, message: '请选择所属部门', trigger: 'change' }],
  user_name: [{ max: 50, message: '使用人姓名不能超过50个字符', trigger: 'blur' }],
}
const activeDepartments = () => props.departments.filter((item) => item.status === 'ACTIVE')

const loadStats = async () => {
  const statuses: InvitationStatus[] = ['UNUSED', 'USED', 'DISABLED']
  const results = await Promise.all(
    statuses.map((status) => invitationApi.list({ page: 1, page_size: 1, status })),
  )
  statuses.forEach((status, index) => { stats[status] = results[index].total })
}
const load = async () => {
  loading.value = true
  try {
    const [data] = await Promise.all([invitationApi.list(query), loadStats()])
    rows.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}
let timer: ReturnType<typeof setTimeout> | undefined
const delayedSearch = () => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    query.page = 1
    load()
  }, 300)
}
const openCreate = () => {
  form.department_id = activeDepartments()[0]?.id || ''
  form.user_name = ''
  formRef.value?.clearValidate()
  dialogVisible.value = true
}
const submit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const item = await invitationApi.create({
      department_id: form.department_id,
      user_name: form.user_name || null,
    })
    dialogVisible.value = false
    ElMessage.success(`邀请码 ${item.code} 生成成功`)
    await load()
  } finally {
    submitting.value = false
  }
}
const copy = async (code: string) => {
  try {
    await navigator.clipboard.writeText(code)
    ElMessage.success('邀请码已复制')
  } catch {
    ElMessage.error('复制失败，请手动复制邀请码')
  }
}
const disable = async (invitation: Invitation) => {
  await ElMessageBox.confirm(
    `停用后邀请码 ${invitation.code} 将无法用于注册，确认停用吗？`,
    '停用邀请码',
    { type: 'warning', confirmButtonText: '确认停用', cancelButtonText: '取消' },
  )
  await invitationApi.disable(invitation.id)
  ElMessage.success('邀请码已停用')
  await load()
}
const statusType = (status: InvitationStatus) =>
  ({ UNUSED: 'warning', USED: 'success', DISABLED: 'danger' } as const)[status]
const statusLabel = (status: InvitationStatus) => INVITATION_STATUS[status]
onMounted(load)
</script>

<template>
  <main class="page organization-page">
    <div class="page-title-row">
      <div>
        <h1>邀请码管理</h1>
        <p>生成并管理内部人员使用的邀请码</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">生成邀请码</el-button>
    </div>
    <div class="organization-filters invite-filters">
      <el-input
        v-model="query.keyword"
        :prefix-icon="Search"
        clearable
        placeholder="搜索邀请码或使用人"
        @input="delayedSearch"
        @clear="load"
      />
      <el-select v-model="query.department_id" clearable placeholder="全部部门" @change="query.page = 1; load()">
        <el-option v-for="department in departments" :key="department.id" :label="department.name" :value="department.id" />
      </el-select>
      <el-select v-model="query.status" clearable placeholder="全部状态" @change="query.page = 1; load()">
        <el-option v-for="(label, key) in INVITATION_STATUS" :key="key" :label="label" :value="key" />
      </el-select>
    </div>
    <div class="invite-summary">
      共 {{ stats.UNUSED + stats.USED + stats.DISABLED }} 个邀请码
      <i />未使用 {{ stats.UNUSED }}<i />已使用 {{ stats.USED }}<i />已停用 {{ stats.DISABLED }}
    </div>
    <section class="surface-card invitation-surface">
      <el-table v-loading="loading" :data="rows" row-key="id">
        <el-table-column prop="code" label="邀请码" min-width="140">
          <template #default="{ row }"><strong class="invite-code">{{ row.code }}</strong></template>
        </el-table-column>
        <el-table-column prop="department_name" label="所属部门" min-width="130" />
        <el-table-column label="使用人姓名" min-width="135">
          <template #default="{ row }">{{ row.user_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="使用状态" width="125">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" effect="light">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">{{ formatDate(row.created_time) }}</template>
        </el-table-column>
        <el-table-column label="使用时间" min-width="170">
          <template #default="{ row }">{{ row.used_time ? formatDate(row.used_time) : '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="CopyDocument" @click="copy(row.code)">复制</el-button>
            <el-button v-if="row.status === 'UNUSED'" link type="danger" @click="disable(row)">停用</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !rows.length" description="暂无符合条件的邀请码" />
      <div class="pagination-row">
        <span>共 {{ total }} 条记录</span>
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

    <el-dialog v-model="dialogVisible" title="生成邀请码" width="530px" class="product-dialog small-dialog">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="所属部门" prop="department_id">
          <el-select v-model="form.department_id" placeholder="请选择部门" style="width: 100%">
            <el-option
              v-for="department in activeDepartments()"
              :key="department.id"
              :label="department.name"
              :value="department.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="使用人姓名（选填）" prop="user_name">
          <el-input v-model="form.user_name" maxlength="50" placeholder="请输入使用人姓名" />
        </el-form-item>
        <div class="blue-note compact">
          <el-icon><InfoFilled /></el-icon>
          <span>邀请码由系统自动生成，每个邀请码仅可绑定一个内部账号</span>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">生成邀请码</el-button>
      </template>
    </el-dialog>
  </main>
</template>
