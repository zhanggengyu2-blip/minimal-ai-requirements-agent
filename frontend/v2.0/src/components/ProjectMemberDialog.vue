<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowDown, ArrowUp, Delete, Plus, Search, UserFilled } from '@element-plus/icons-vue'
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
const userMap = computed(() => new Map(users.value.map((user) => [user.id, user])))
const orderedMembers = computed(() => selectedIds.value.map((userId) => {
  const member = memberMap.value.get(userId)
  const user = userMap.value.get(userId)
  return {
    id: userId,
    name: user?.name ?? member?.name ?? '未知成员',
    department_name: user?.department_name ?? member?.department_name ?? '',
    role: user?.role ?? member?.role ?? 'MEMBER',
    task_count: member?.task_count ?? 0,
  }
}))
const availableUsers = computed(() => {
  const normalized = keyword.value.trim().toLowerCase()
  return users.value.filter((user) => {
    if (selectedIds.value.includes(user.id)) return false
    if (!normalized) return true
    return `${user.name} ${user.department_name}`.toLowerCase().includes(normalized)
  })
})

const moveMember = (index: number, offset: -1 | 1) => {
  const target = index + offset
  if (target < 0 || target >= selectedIds.value.length) return
  const next = [...selectedIds.value]
  ;[next[index], next[target]] = [next[target], next[index]]
  selectedIds.value = next
}
const addMember = (userId: string) => {
  if (!selectedIds.value.includes(userId)) selectedIds.value = [...selectedIds.value, userId]
}
const removeMember = (userId: string) => {
  const taskCount = memberMap.value.get(userId)?.task_count ?? 0
  if (taskCount > 0) {
    ElMessage.warning('该成员仍负责任务，请先转交任务')
    return
  }
  selectedIds.value = selectedIds.value.filter((id) => id !== userId)
}

const close = () => emit('update:modelValue', false)
const load = async () => {
  if (!props.project) return
  loading.value = true
  conflictMessage.value = ''
  try {
    const [members, directory] = await Promise.all([
      projectApi.listMembers(props.project.id),
      userApi.listAll(),
    ])
    currentMembers.value = members.items
    selectedIds.value = members.items.map((member) => member.user_id)
    memberRevision.value = members.member_revision
    users.value = directory
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
    <section class="member-order-section">
      <div class="member-section-heading">
        <strong>当前项目成员</strong>
        <span>此顺序用于团队任务、甘特图和版本参与人员</span>
      </div>
      <div v-loading="loading" class="member-directory ordered-member-directory">
        <div v-for="(member, index) in orderedMembers" :key="member.id" class="member-option ordered-member-option">
          <span class="member-option-avatar"><el-icon><UserFilled /></el-icon></span>
          <span class="member-option-info">
            <strong>{{ member.name }}</strong>
            <small>{{ member.department_name }} · {{ member.role === 'ADMIN' ? '管理员' : '成员' }}</small>
          </span>
          <span v-if="member.task_count" class="member-task-count">
            {{ member.task_count }} 个任务
          </span>
          <div class="member-order-actions">
            <el-button
              circle
              size="small"
              :icon="ArrowUp"
              :disabled="project?.status === 'ARCHIVED' || index === 0"
              aria-label="上移成员"
              @click="moveMember(index, -1)"
            />
            <el-button
              circle
              size="small"
              :icon="ArrowDown"
              :disabled="project?.status === 'ARCHIVED' || index === orderedMembers.length - 1"
              aria-label="下移成员"
              @click="moveMember(index, 1)"
            />
            <el-button
              circle
              size="small"
              type="danger"
              plain
              :icon="Delete"
              :disabled="project?.status === 'ARCHIVED' || member.task_count > 0"
              aria-label="移除成员"
              @click="removeMember(member.id)"
            />
          </div>
        </div>
        <el-empty v-if="!loading && !orderedMembers.length" description="项目至少需要一名成员" />
      </div>
    </section>

    <section class="member-add-section">
      <div class="member-section-heading">
        <strong>添加注册用户</strong>
        <span>新成员将追加到当前顺序末尾</span>
      </div>
      <el-input v-model="keyword" :prefix-icon="Search" clearable placeholder="搜索姓名或部门" class="member-search" />
      <div class="member-directory available-member-directory">
        <div v-for="user in availableUsers" :key="user.id" class="member-option">
          <span class="member-option-avatar"><el-icon><UserFilled /></el-icon></span>
          <span class="member-option-info">
            <strong>{{ user.name }}</strong>
            <small>{{ user.department_name }} · {{ user.role === 'ADMIN' ? '管理员' : '成员' }}</small>
          </span>
          <el-button
            type="primary"
            link
            :icon="Plus"
            :disabled="project?.status === 'ARCHIVED'"
            @click="addMember(user.id)"
          >添加</el-button>
        </div>
        <el-empty v-if="!loading && !availableUsers.length" description="没有可添加的注册用户" />
      </div>
    </section>

    <p class="member-dialog-tip">仍负责任务的成员不能移除；成员顺序保存后由整个项目共用。</p>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button v-if="conflictMessage" :loading="loading" @click="load">刷新成员</el-button>
      <el-button type="primary" :loading="submitting" :disabled="project?.status === 'ARCHIVED'" @click="save">保存成员</el-button>
    </template>
  </el-dialog>
</template>
