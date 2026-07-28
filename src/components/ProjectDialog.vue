<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { FolderAdd } from '@element-plus/icons-vue'
import { projectApi } from '../api'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; created: [] }>()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const form = reactive({ name: '', project_context: '', description: '' })
const rules: FormRules = {
  name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { max: 100, message: '项目名称不能超过100个字符', trigger: 'blur' },
  ],
  project_context: [
    { required: true, message: '请输入项目背景与上下文', trigger: 'blur' },
    { max: 10000, message: '项目上下文不能超过10000个字符', trigger: 'blur' },
  ],
  description: [{ max: 2000, message: '项目简介不能超过2000个字符', trigger: 'blur' }],
}

watch(() => props.modelValue, (visible) => {
  if (!visible) return
  Object.assign(form, { name: '', project_context: '', description: '' })
  formRef.value?.clearValidate()
})

const close = () => emit('update:modelValue', false)
const submit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    ElMessage.warning('请填写项目名称和项目背景与上下文')
    return
  }
  submitting.value = true
  try {
    await projectApi.create({ ...form })
    ElMessage.success('项目创建成功')
    emit('created')
    close()
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    width="572px"
    class="product-dialog"
    :close-on-click-modal="false"
    @close="close"
  >
    <template #header>
      <div class="dialog-heading">
        <h2>新建项目</h2>
        <p>创建独立项目空间，用于收集、分析和管理该项目的需求</p>
      </div>
    </template>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="项目名称" prop="name">
        <el-input v-model="form.name" maxlength="100" placeholder="例如：智能客服平台" />
        <div class="field-tip">项目名称不可重复</div>
      </el-form-item>
      <el-form-item label="项目背景与上下文" prop="project_context">
        <el-input
          v-model="form.project_context"
          type="textarea"
          :rows="4"
          maxlength="10000"
          show-word-limit
          placeholder="描述项目目标、业务范围、目标用户及判断需求所需的背景信息"
        />
        <div class="field-tip">AI 将依据这些信息理解并分析项目需求</div>
      </el-form-item>
      <el-form-item label="项目简介（选填）" prop="description">
        <el-input v-model="form.description" maxlength="2000" placeholder="一句话概括项目" />
      </el-form-item>
      <div class="blue-note">
        <el-icon :size="27"><FolderAdd /></el-icon>
        <div>
          <strong>创建项目后，即可提交和集中管理需求</strong>
          <p>新提交需求将自动进入 AI 分析，并生成标准化结果</p>
        </div>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">创建项目</el-button>
    </template>
  </el-dialog>
</template>
