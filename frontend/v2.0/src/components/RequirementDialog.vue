<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { MagicStick } from '@element-plus/icons-vue'
import type { Project } from '../api'
import { requirementApi } from '../api'

const props = defineProps<{
  modelValue: boolean
  projects: Project[]
  defaultProjectId?: string
}>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: [failed: boolean]
}>()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const form = reactive({ project_id: '', raw_content: '' })
const rules: FormRules = {
  project_id: [{ required: true, message: '请选择所属项目', trigger: 'change' }],
  raw_content: [
    { required: true, message: '请输入需求描述', trigger: 'blur' },
    { max: 10000, message: '需求描述不能超过10000个字符', trigger: 'blur' },
  ],
}

watch(() => props.modelValue, (visible) => {
  if (!visible) return
  form.project_id = props.defaultProjectId || props.projects[0]?.id || ''
  form.raw_content = ''
  formRef.value?.clearValidate()
})

const close = () => emit('update:modelValue', false)
const submit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    ElMessage.warning('请完整填写所属项目和需求描述')
    return
  }
  submitting.value = true
  try {
    const result = await requirementApi.create({ ...form })
    const failed = result.analysis_status === 'FAILED'
    if (failed) {
      ElMessage.warning('需求保存成功，但AI分析失败，可稍后重试')
    } else {
      ElMessage.success('需求提交成功，AI 分析已完成')
    }
    emit('created', failed)
    close()
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    width="596px"
    class="product-dialog"
    :close-on-click-modal="false"
    @close="close"
  >
    <template #header>
      <div class="dialog-heading">
        <h2>提交新需求</h2>
        <p>填写需求信息，提交后系统将自动生成需求编号并发起 AI 分析</p>
      </div>
    </template>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="所属项目" prop="project_id">
        <el-select v-model="form.project_id" placeholder="请选择项目" style="width: 100%">
          <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="需求描述" prop="raw_content">
        <el-input
          v-model="form.raw_content"
          type="textarea"
          :rows="7"
          maxlength="10000"
          show-word-limit
          placeholder="请尽量清晰地说明使用场景、现状问题、期望结果和业务价值"
        />
      </el-form-item>
      <div class="blue-note compact">
        <el-icon :size="20"><MagicStick /></el-icon>
        <span>提交后 AI 将自动分析并给出建议，不会自动修改需求内容</span>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">提交需求</el-button>
    </template>
  </el-dialog>
</template>
