<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import {
  taskApi,
  type ProjectMember,
  type Task,
  type TaskCreate,
  type TaskPriority,
  type TaskStatus,
} from '../api'
import { ApiRequestError } from '../api/http'

const props = withDefaults(defineProps<{
  modelValue: boolean
  projectId: string
  members: ReadonlyArray<ProjectMember>
  task?: Task | null
  initialAssigneeId?: string
  readOnly?: boolean
}>(), { task: null, initialAssigneeId: '', readOnly: false })
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  changed: []
}>()

interface TaskForm {
  name: string
  assignee_id: string
  status: TaskStatus
  priority: TaskPriority
  version_id: string | null
  start_date: string | null
  due_date: string | null
  description: string
}

const emptyForm = (): TaskForm => ({
  name: '',
  assignee_id: '',
  status: 'NOT_STARTED',
  priority: 'P1',
  version_id: null,
  start_date: null,
  due_date: null,
  description: '',
})
const formRef = ref<FormInstance>()
const form = reactive<TaskForm>(emptyForm())
const currentTask = ref<Task | null>(null)
const submitting = ref(false)
const refreshing = ref(false)
const deleteVisible = ref(false)
const deleting = ref(false)
const conflictMessage = ref('')
const actionError = ref('')
const isEditing = computed(() => Boolean(currentTask.value))
const dialogTitle = computed(() => props.readOnly ? '查看任务' : isEditing.value ? '编辑任务' : '新建任务')

const rules: FormRules<TaskForm> = {
  name: [
    { required: true, message: '请输入任务名称', trigger: 'blur' },
    { max: 200, message: '任务名称不能超过200个字符', trigger: 'blur' },
  ],
  assignee_id: [{ required: true, message: '请选择负责人', trigger: 'change' }],
  status: [{ required: true, message: '请选择任务状态', trigger: 'change' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }],
  description: [{ max: 500, message: '任务说明不能超过500个字符', trigger: 'blur' }],
}

const assignTaskToForm = (task: Task) => {
  Object.assign(form, {
    name: task.name,
    assignee_id: task.assignee_id,
    status: task.status,
    priority: task.priority,
    version_id: task.version_id,
    start_date: task.start_date,
    due_date: task.due_date,
    description: task.description,
  })
}
const resetFromProps = () => {
  currentTask.value = props.task ? { ...props.task } : null
  Object.assign(form, emptyForm())
  if (props.task) assignTaskToForm(props.task)
  else form.assignee_id = props.initialAssigneeId
  conflictMessage.value = ''
  actionError.value = ''
  deleteVisible.value = false
  void nextTick(() => formRef.value?.clearValidate())
}
const close = () => {
  if (!submitting.value && !deleting.value) emit('update:modelValue', false)
}
const validateDates = () => {
  if (form.start_date && form.due_date && form.start_date > form.due_date) {
    actionError.value = '开始日期不能晚于截止日期'
    return false
  }
  return true
}
const handleFailure = (error: unknown, action: 'create' | 'save' | 'delete') => {
  if (!(error instanceof ApiRequestError)) return
  if (error.code === 'TASK_ASSIGNEE_LIMIT_REACHED') {
    actionError.value = action === 'create'
      ? '创建失败：该成员已达到任务上限'
      : '保存失败：该成员已达到任务上限'
  } else if (error.code?.includes('REVISION_CONFLICT')) {
    conflictMessage.value = '任务已被其他人修改，请加载最新内容后再继续。'
  } else if (error.code === 'PROJECT_ARCHIVED') {
    actionError.value = '项目已归档，仅支持查看任务。'
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
    const base: TaskCreate = {
      name: form.name.trim(),
      assignee_id: form.assignee_id,
      status: form.status,
      priority: form.priority,
      version_id: form.version_id,
      start_date: form.start_date,
      due_date: form.due_date,
      description: form.description.trim(),
    }
    if (currentTask.value) {
      await taskApi.update(props.projectId, currentTask.value.id, {
        expected_revision: currentTask.value.revision,
        ...base,
      })
      ElMessage.success('任务已更新')
    } else {
      await taskApi.create(props.projectId, base)
      ElMessage.success('任务已创建')
    }
    emit('changed')
    emit('update:modelValue', false)
  } catch (error) {
    handleFailure(error, currentTask.value ? 'save' : 'create')
  } finally {
    submitting.value = false
  }
}

const refreshLatest = async () => {
  if (!currentTask.value) return
  refreshing.value = true
  try {
    const latest = await taskApi.detail(props.projectId, currentTask.value.id)
    currentTask.value = latest
    assignTaskToForm(latest)
    conflictMessage.value = ''
    actionError.value = ''
  } catch (error) {
    handleFailure(error, 'save')
  } finally {
    refreshing.value = false
  }
}

const confirmDelete = async () => {
  if (!currentTask.value || props.readOnly) return
  deleting.value = true
  actionError.value = ''
  try {
    await taskApi.delete(props.projectId, currentTask.value.id, currentTask.value.revision)
    ElMessage.success('任务已删除')
    deleteVisible.value = false
    emit('changed')
    emit('update:modelValue', false)
  } catch (error) {
    deleteVisible.value = false
    handleFailure(error, 'delete')
  } finally {
    deleting.value = false
  }
}

watch(() => props.modelValue, (visible) => {
  if (visible) resetFromProps()
})
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    width="520px"
    class="product-dialog task-dialog"
    :close-on-click-modal="false"
    destroy-on-close
    @close="close"
  >
    <template #header>
      <div class="dialog-heading">
        <h2>{{ dialogTitle }}</h2>
        <p v-if="readOnly">归档项目或非项目成员仅支持查看</p>
      </div>
    </template>

    <el-alert
      v-if="conflictMessage"
      :title="conflictMessage"
      type="error"
      show-icon
      :closable="false"
      class="task-dialog-alert"
    >
      <template #default>
        <el-button link type="primary" :loading="refreshing" @click="refreshLatest">加载最新内容</el-button>
      </template>
    </el-alert>
    <el-alert
      v-if="actionError"
      :title="actionError"
      type="error"
      show-icon
      :closable="false"
      class="task-dialog-alert"
    />

    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" :disabled="readOnly">
      <el-form-item label="任务名称" prop="name">
        <el-input v-model="form.name" maxlength="200" placeholder="请输入任务名称" />
      </el-form-item>
      <div class="task-form-grid">
        <el-form-item label="负责人" prop="assignee_id">
          <el-select v-model="form.assignee_id" placeholder="请选择负责人" filterable>
            <el-option v-for="member in members" :key="member.user_id" :label="member.name" :value="member.user_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务状态" prop="status">
          <el-select v-model="form.status">
            <el-option label="未开始" value="NOT_STARTED" />
            <el-option label="进行中" value="IN_PROGRESS" />
            <el-option label="已完成" value="COMPLETED" />
            <el-option label="已取消" value="CANCELED" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="form.priority">
            <el-option label="P0 · 重要且紧急" value="P0" />
            <el-option label="P1 · 重要不紧急" value="P1" />
            <el-option label="P2 · 紧急不重要" value="P2" />
            <el-option label="P3 · 不重要不紧急" value="P3" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属版本（选填）">
          <el-select :model-value="form.version_id" disabled placeholder="T6 接入版本后可选" />
        </el-form-item>
        <el-form-item label="开始日期（选填）">
          <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" placeholder="选择开始日期" />
        </el-form-item>
        <el-form-item label="截止日期（选填）">
          <el-date-picker v-model="form.due_date" type="date" value-format="YYYY-MM-DD" placeholder="选择截止日期" />
        </el-form-item>
      </div>
      <el-form-item label="任务说明（选填）" prop="description">
        <el-input v-model="form.description" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="补充任务范围、完成标准或注意事项" />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="task-dialog-footer">
        <el-button
          v-if="isEditing && !readOnly"
          type="danger"
          plain
          :icon="Delete"
          @click="deleteVisible = true"
        >删除任务</el-button>
        <span />
        <el-button @click="close">{{ readOnly ? '关闭' : '取消' }}</el-button>
        <el-button v-if="!readOnly" type="primary" :loading="submitting" @click="submit">
          {{ isEditing ? '保存' : '创建任务' }}
        </el-button>
      </div>
    </template>
  </el-dialog>

  <el-dialog
    v-model="deleteVisible"
    width="505px"
    class="product-dialog task-delete-dialog"
    append-to-body
    :close-on-click-modal="false"
  >
    <div class="task-delete-content">
      <span class="task-delete-warning">!</span>
      <div><h3>删除任务</h3><p>删除后任务将无法恢复，确认删除该任务吗？</p></div>
    </div>
    <template #footer>
      <el-button @click="deleteVisible = false">取消</el-button>
      <el-button type="danger" :loading="deleting" @click="confirmDelete">确认删除</el-button>
    </template>
  </el-dialog>
</template>
