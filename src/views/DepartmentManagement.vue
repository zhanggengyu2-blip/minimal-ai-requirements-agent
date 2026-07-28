<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { InfoFilled, Plus, Search } from '@element-plus/icons-vue'
import type { Department, DepartmentStatus } from '../api'
import { departmentApi } from '../api'
import { DEPARTMENT_STATUS, formatDate } from '../constants'

const emit = defineEmits<{ changed: [] }>()
const loading = ref(false)
const submitting = ref(false)
const rows = ref<Department[]>([])
const total = ref(0)
const dialogVisible = ref(false)
const editing = ref<Department | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({ name: '' })
const query = reactive<{
  page: number
  page_size: number
  keyword?: string
  status?: DepartmentStatus
}>({ page: 1, page_size: 10 })
const rules: FormRules = {
  name: [
    { required: true, message: '请输入部门名称', trigger: 'blur' },
    { max: 100, message: '部门名称不能超过100个字符', trigger: 'blur' },
  ],
}
const dialogTitle = computed(() => editing.value ? '编辑部门' : '新增部门')

const load = async () => {
  loading.value = true
  try {
    const data = await departmentApi.list(query)
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
  editing.value = null
  form.name = ''
  formRef.value?.clearValidate()
  dialogVisible.value = true
}
const openEdit = (department: Department) => {
  editing.value = department
  form.name = department.name
  formRef.value?.clearValidate()
  dialogVisible.value = true
}
const submit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (editing.value) {
      await departmentApi.update(editing.value.id, { name: form.name })
      ElMessage.success('部门名称已更新')
    } else {
      await departmentApi.create({ name: form.name })
      ElMessage.success('部门新增成功')
    }
    dialogVisible.value = false
    await load()
    emit('changed')
  } finally {
    submitting.value = false
  }
}
const toggleStatus = async (department: Department) => {
  const disabling = department.status === 'ACTIVE'
  await ElMessageBox.confirm(
    disabling
      ? `停用后，“${department.name}”将不再用于注册和生成邀请码，确认停用吗？`
      : `确认重新启用“${department.name}”吗？`,
    disabling ? '停用部门' : '启用部门',
    { type: disabling ? 'warning' : 'info', confirmButtonText: '确认', cancelButtonText: '取消' },
  )
  await departmentApi.update(department.id, { status: disabling ? 'DISABLED' : 'ACTIVE' })
  ElMessage.success(disabling ? '部门已停用' : '部门已启用')
  await load()
  emit('changed')
}
onMounted(load)
</script>

<template>
  <main class="page organization-page">
    <div class="page-title-row">
      <div>
        <h1>部门管理</h1>
        <p>维护内部人员可选择的一级部门</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">新增部门</el-button>
    </div>
    <div class="organization-note">
      <el-icon><InfoFilled /></el-icon>
      <span>仅支持一级部门；已关联用户或项目的部门不可删除，只能停用。</span>
    </div>
    <div class="organization-filters">
      <el-input
        v-model="query.keyword"
        :prefix-icon="Search"
        clearable
        maxlength="100"
        placeholder="搜索部门名称"
        @input="delayedSearch"
        @clear="load"
      />
      <el-select v-model="query.status" clearable placeholder="全部状态" @change="query.page = 1; load()">
        <el-option v-for="(label, key) in DEPARTMENT_STATUS" :key="key" :label="label" :value="key" />
      </el-select>
    </div>
    <section v-loading="loading" class="department-list">
      <article v-for="department in rows" :key="department.id" class="department-card">
        <div class="department-identity">
          <strong>{{ department.name }}</strong>
          <span>DEPT-{{ department.id.slice(-6).toUpperCase() }}</span>
        </div>
        <el-tag :type="department.status === 'ACTIVE' ? 'success' : 'info'" effect="light">
          {{ DEPARTMENT_STATUS[department.status] }}
        </el-tag>
        <div class="department-data"><label>创建时间</label>{{ formatDate(department.created_time).slice(0, 10) }}</div>
        <div class="department-data"><label>更新时间</label>{{ formatDate(department.updated_time).slice(0, 10) }}</div>
        <div class="department-data">
          <label>关联信息</label>{{ department.user_count }} 人 · {{ department.project_count }} 个项目
        </div>
        <div class="department-actions">
          <el-button link type="primary" @click="openEdit(department)">编辑</el-button>
          <i />
          <el-button
            link
            :type="department.status === 'ACTIVE' ? 'danger' : 'success'"
            @click="toggleStatus(department)"
          >
            {{ department.status === 'ACTIVE' ? '停用' : '启用' }}
          </el-button>
        </div>
      </article>
      <el-empty v-if="!loading && !rows.length" description="暂无符合条件的部门" />
    </section>
    <div class="pagination-row">
      <span>共 {{ total }} 个部门</span>
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="sizes, prev, pager, next"
        @change="load"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="552px" class="product-dialog small-dialog">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="部门名称" prop="name">
          <el-input v-model="form.name" maxlength="100" placeholder="请输入部门名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">
          {{ editing ? '保存修改' : '确认新增' }}
        </el-button>
      </template>
    </el-dialog>
  </main>
</template>
