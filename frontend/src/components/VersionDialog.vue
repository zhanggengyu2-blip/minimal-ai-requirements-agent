<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { User } from '@element-plus/icons-vue'
import {
  versionApi,
  type ProjectMember,
  type ProjectVersion,
  type VersionCreate,
} from '../api'
import { ApiRequestError } from '../api/http'

const props = withDefaults(defineProps<{
  modelValue: boolean
  projectId: string
  members: ReadonlyArray<ProjectMember>
  version?: ProjectVersion | null
  readOnly?: boolean
}>(), { version: null, readOnly: false })
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [version: ProjectVersion]
}>()

interface VersionForm {
  name: string
  start_date: string
  end_date: string
  participant_ids: string[]
}

const emptyForm = (): VersionForm => ({ name: '', start_date: '', end_date: '', participant_ids: [] })
const formRef = ref<FormInstance>()
const form = reactive<VersionForm>(emptyForm())
const currentVersion = ref<ProjectVersion | null>(null)
const submitting = ref(false)
const refreshing = ref(false)
const actionError = ref('')
const conflictMessage = ref('')
const isEditing = computed(() => Boolean(currentVersion.value))
const title = computed(() => isEditing.value ? '编辑版本' : '创建新版本')
const selectedMembers = computed(() => props.members.filter((member) => form.participant_ids.includes(member.user_id)))
const blockedParticipantIds = computed(() => new Set(
  currentVersion.value?.participants
    .filter((participant) => participant.task_count > 0)
    .map((participant) => participant.user_id) || [],
))
const rules: FormRules<VersionForm> = {
  name: [
    { required: true, message: '请输入版本名称', trigger: 'blur' },
    { max: 100, message: '版本名称不能超过100个字符', trigger: 'blur' },
  ],
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  end_date: [{ required: true, message: '请选择结束日期', trigger: 'change' }],
  participant_ids: [{ type: 'array', required: true, min: 1, message: '请至少选择一名参与人员', trigger: 'change' }],
}

const assignVersion = (version: ProjectVersion) => {
  Object.assign(form, {
    name: version.name,
    start_date: version.start_date,
    end_date: version.end_date,
    participant_ids: version.participants.map((participant) => participant.user_id),
  })
}
const resetFromProps = () => {
  currentVersion.value = props.version ? { ...props.version, participants: [...props.version.participants] } : null
  Object.assign(form, emptyForm())
  if (currentVersion.value) assignVersion(currentVersion.value)
  actionError.value = ''
  conflictMessage.value = ''
  void nextTick(() => formRef.value?.clearValidate())
}
const close = () => {
  if (!submitting.value) emit('update:modelValue', false)
}
const validateDates = () => {
  if (form.start_date && form.end_date && form.start_date > form.end_date) {
    actionError.value = '结束日期不能早于开始日期'
    return false
  }
  return true
}
const handleFailure = (error: unknown) => {
  if (!(error instanceof ApiRequestError)) return
  if (error.code === 'VERSION_REVISION_CONFLICT' || error.code?.includes('REVISION_CONFLICT')) {
    conflictMessage.value = '版本已被其他人修改，请加载最新内容后再继续。'
  } else if (error.code === 'VERSION_PARTICIPANT_HAS_TASKS') {
    actionError.value = '仍负责任务的参与人员不能移除，请先转交任务或将任务移出当前版本。'
  } else if (error.code === 'VERSION_NAME_ALREADY_EXISTS') {
    actionError.value = '当前项目已存在同名版本。'
  } else if (error.code === 'VERSION_DATE_ORDER_INVALID') {
    actionError.value = '结束日期不能早于开始日期。'
  } else if (error.code === 'PROJECT_ARCHIVED') {
    actionError.value = '项目已归档，仅支持查看版本。'
  } else {
    actionError.value = error.message
  }
}
const submit = async () => {
  if (props.readOnly) return
  actionError.value = ''
  conflictMessage.value = ''
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid || !validateDates()) return
  submitting.value = true
  try {
    const payload: VersionCreate = {
      name: form.name.trim(),
      start_date: form.start_date,
      end_date: form.end_date,
      participant_ids: [...form.participant_ids],
    }
    const saved = currentVersion.value
      ? await versionApi.update(props.projectId, currentVersion.value.id, {
          expected_revision: currentVersion.value.revision,
          ...payload,
        })
      : await versionApi.create(props.projectId, payload)
    ElMessage.success(currentVersion.value ? '版本已更新' : '版本已创建')
    emit('saved', saved)
    emit('update:modelValue', false)
  } catch (error) {
    handleFailure(error)
  } finally {
    submitting.value = false
  }
}
const refreshLatest = async () => {
  if (!currentVersion.value) return
  refreshing.value = true
  try {
    const latest = await versionApi.detail(props.projectId, currentVersion.value.id)
    currentVersion.value = latest
    assignVersion(latest)
    actionError.value = ''
    conflictMessage.value = ''
  } catch (error) {
    handleFailure(error)
  } finally {
    refreshing.value = false
  }
}
const removeParticipant = (userId: string) => {
  if (blockedParticipantIds.value.has(userId)) {
    actionError.value = '该成员仍负责当前版本任务，请先转交任务或将任务移出版本。'
    return
  }
  form.participant_ids = form.participant_ids.filter((id) => id !== userId)
}
const clearParticipants = () => {
  form.participant_ids = form.participant_ids.filter((id) => blockedParticipantIds.value.has(id))
}

watch(() => props.modelValue, (visible) => {
  if (visible) resetFromProps()
})
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    width="536px"
    class="product-dialog version-dialog"
    :close-on-click-modal="false"
    destroy-on-close
    @close="close"
  >
    <template #header><div class="dialog-heading"><h2>{{ title }}</h2></div></template>

    <el-alert v-if="conflictMessage" :title="conflictMessage" type="error" show-icon :closable="false" class="version-dialog-alert">
      <template #default><el-button link type="primary" :loading="refreshing" @click="refreshLatest">加载最新内容</el-button></template>
    </el-alert>
    <el-alert v-if="actionError" :title="actionError" type="error" show-icon :closable="false" class="version-dialog-alert" />

    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" :disabled="readOnly">
      <el-form-item label="版本名称" prop="name">
        <el-input v-model="form.name" maxlength="100" placeholder="请输入版本名称" />
      </el-form-item>
      <el-form-item label="开始日期" prop="start_date">
        <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" placeholder="选择开始日期" />
      </el-form-item>
      <el-form-item label="结束日期" prop="end_date">
        <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" placeholder="选择结束日期" />
      </el-form-item>
      <el-form-item label="参与人员" prop="participant_ids">
        <el-select
          v-model="form.participant_ids"
          multiple
          filterable
          collapse-tags
          collapse-tags-tooltip
          :prefix-icon="User"
          placeholder="添加参与人员"
        >
          <el-option
            v-for="member in members"
            :key="member.user_id"
            :label="`${member.name} · ${member.department_name}`"
            :value="member.user_id"
            :disabled="blockedParticipantIds.has(member.user_id)"
          />
        </el-select>
      </el-form-item>

      <section class="version-selected-members">
        <header><strong>已选人员（{{ selectedMembers.length }}）</strong><el-button link :disabled="readOnly || !selectedMembers.length" @click="clearParticipants">清空</el-button></header>
        <div v-if="selectedMembers.length" class="version-selected-list">
          <div v-for="member in selectedMembers" :key="member.user_id" class="version-selected-member">
            <span class="version-member-avatar">{{ member.name.slice(0, 1) }}</span>
            <div><strong>{{ member.name }}</strong><small v-if="member.department_name">{{ member.department_name }}</small></div>
            <el-tooltip v-if="blockedParticipantIds.has(member.user_id)" content="该成员仍负责当前版本任务，暂不能移除" placement="left">
              <el-button link disabled>移除</el-button>
            </el-tooltip>
            <el-button v-else link :disabled="readOnly" @click="removeParticipant(member.user_id)">移除</el-button>
          </div>
        </div>
        <el-empty v-else :image-size="52" description="尚未选择参与人员" />
      </section>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button v-if="!readOnly" type="primary" :loading="submitting" @click="submit">
        {{ isEditing ? '保存修改' : '创建版本' }}
      </el-button>
    </template>
  </el-dialog>
</template>
