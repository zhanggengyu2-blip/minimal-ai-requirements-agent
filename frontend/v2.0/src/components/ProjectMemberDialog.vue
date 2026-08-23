<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, UserFilled } from '@element-plus/icons-vue'
import { projectApi, userApi, type Project, type ProjectMember, type User } from '../api'
import { ApiRequestError } from '../api/http'

const props = defineProps<{ modelValue: boolean; project: Project | null }>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: []
}>()

const loading = ref(false)
const submitting = ref(false)
const users = ref<User[]>([])
const currentMembers = ref<ProjectMember[]>([])
const selectedIds = ref<string[]>([])
const memberRevision = ref(1)
const keyword = ref('')
const conflictMessage = ref('')

const memberMap = computed(() => new Map(currentMembers.value.map((member) => [member.user_id, member])))
const filteredUsers = computed(() => {
  const normalized = keyword.value.trim().toLowerCase()
  if (!normalized) return users.value
  return users.value.filter((user) =>
    `${user.name} ${user.department_name}`.toLowerCase().includes(normalized),
  )
})

const close = () => emit('update:modelValue', false)
const load = async () => {
  if (!props.project) return
  loading.value = true
  conflictMessage.value = ''
  try {
    const [members, directory] = await Promise.all([
      projectApi.listMembers(props.project.id),
      userApi.list({ page: 1, page_size: 100 }),
    ])
    currentMembers.value = members.items
    selectedIds.value = members.items.map((member) => member.user_id)
    memberRevision.value = members.member_revision
    users.value = directory.items
  } finally {
    loading.value = false
  }
}

const save = async () => {
  if (!props.project) return
  if (!selectedIds.value.length) {
    ElMessage.warning('项目至少需要保留一名成员')
    return
  }
  submitting.value = true
  conflictMessage.value = ''
  try {
    const result = await projectApi.saveMembers(props.project.id, {
      user_ids: selectedIds.value,
      expected_member_revision: memberRevision.value,
    })
    currentMembers.value = result.items
    memberRevision.value = result.member_revision
    ElMessage.success('项目成员已更新')
    emit('saved')
    close()
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 409) {
      conflictMessage.value = error.message
    }
  } finally {
    submitting.value = false
  }
}

watch(() => props.modelValue, (visible) => {
  if (!visible) return
  keyword.value = ''
  void load()
})
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    width="650px"
    class="product-dialog member-dialog"
    :close-on-click-modal="false"
    @close="close"
  >
    <template #header>
      <div class="dialog-heading">
        <h2>管理项目成员</h2>
        <p>{{ project?.name }} · 已选择 {{ selectedIds.length }} 人</p>
      </div>
    </template>

    <el-alert
      v-if="project?.status === 'ARCHIVED'"
      title="归档项目仅支持查看成员；重新打开项目后才能修改。"
      type="warning"
      show-icon
      :closable="false"
    />
    <el-alert
      v-if="conflictMessage"
      :title="conflictMessage"
      description="已保留当前选择，请刷新成员列表后重新确认。"
      type="error"
      show-icon
      :closable="false"
      class="member-conflict"
    />
    <el-input v-model="keyword" :prefix-icon="Search" clearable placeholder="搜索姓名或部门" class="member-search" />

    <div v-loading="loading" class="member-directory">
      <el-checkbox-group v-model="selectedIds">
        <label v-for="user in filteredUsers" :key="user.id" class="member-option">
          <el-checkbox :value="user.id" :disabled="project?.status === 'ARCHIVED'" />
          <span class="member-option-avatar"><el-icon><UserFilled /></el-icon></span>
          <span class="member-option-info">
            <strong>{{ user.name }}</strong>
            <small>{{ user.department_name }} · {{ user.role === 'ADMIN' ? '管理员' : '成员' }}</small>
          </span>
          <span v-if="memberMap.get(user.id)?.task_count" class="member-task-count">
            {{ memberMap.get(user.id)?.task_count }} 个任务
          </span>
        </label>
      </el-checkbox-group>
      <el-empty v-if="!loading && !filteredUsers.length" description="没有匹配的内部用户" />
    </div>

    <p class="member-dialog-tip">仍负责任务的成员不能移除；保存时会由服务端再次校验。</p>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button v-if="conflictMessage" :loading="loading" @click="load">刷新成员</el-button>
      <el-button type="primary" :loading="submitting" :disabled="project?.status === 'ARCHIVED'" @click="save">保存成员</el-button>
    </template>
  </el-dialog>
</template>
