<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Lock, Right, User } from '@element-plus/icons-vue'
import AuthLayout from '../layouts/AuthLayout.vue'
import { authApi, type LoginDepartment } from '../api'
import { ApiRequestError } from '../api/http'
import { useCurrentUser } from '../composables/useCurrentUser'

type AuthMode = 'login' | 'register'

const route = useRoute()
const router = useRouter()
const auth = useCurrentUser()
const mode = ref<AuthMode>('login')
const departments = ref<LoginDepartment[]>([])
const departmentsLoading = ref(false)
const submitting = ref(false)
const errorMessage = ref('')
const formRef = ref<FormInstance>()
const form = reactive({ department_id: '', name: '', credential: '' })

const isLogin = computed(() => mode.value === 'login')
const title = computed(() => isLogin.value ? '登录工作台' : '首次注册')
const subtitle = computed(() => isLogin.value
  ? '使用部门、姓名和公司统一密码登录'
  : '使用管理员提供的邀请码完成首次注册')
const credentialLabel = computed(() => isLogin.value ? '公司统一密码' : '邀请码')
const credentialPlaceholder = computed(() => isLogin.value ? '请输入公司统一密码' : '请输入邀请码')
const rules: FormRules = {
  department_id: [{ required: true, message: '请选择所属部门', trigger: 'change' }],
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { max: 50, message: '姓名不能超过 50 个字符', trigger: 'blur' },
  ],
  credential: [{ required: true, message: '请输入登录凭据', trigger: 'blur' }],
}

const loadDepartments = async () => {
  departmentsLoading.value = true
  try {
    departments.value = await authApi.departments()
    if (!form.department_id && departments.value.length === 1) {
      form.department_id = departments.value[0].id
    }
  } finally {
    departmentsLoading.value = false
  }
}

const switchMode = (nextMode: AuthMode) => {
  if (mode.value === nextMode) return
  mode.value = nextMode
  form.credential = ''
  errorMessage.value = ''
  formRef.value?.clearValidate('credential')
}

const safeRedirect = () => {
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/projects'
  return redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : '/projects'
}

const submit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  errorMessage.value = ''
  try {
    if (isLogin.value) {
      await auth.login({
        department_id: form.department_id,
        name: form.name,
        shared_password: form.credential,
      })
      ElMessage.success('登录成功')
    } else {
      await auth.register({
        department_id: form.department_id,
        name: form.name,
        invitation_code: form.credential,
      })
      ElMessage.success('注册成功，已进入工作台')
    }
    await router.replace(safeRedirect())
  } catch (error) {
    errorMessage.value = error instanceof ApiRequestError ? error.message : '认证失败，请稍后重试'
    form.credential = ''
  } finally {
    submitting.value = false
  }
}

defineExpose({ form, mode, switchMode, submit })
onMounted(loadDepartments)
</script>

<template>
  <AuthLayout>
    <div class="auth-card">
      <div class="auth-mode-switch" role="tablist" aria-label="认证方式">
        <button
          type="button"
          role="tab"
          :aria-selected="isLogin"
          :class="{ active: isLogin }"
          @click="switchMode('login')"
        >
          登录
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="!isLogin"
          :class="{ active: !isLogin }"
          @click="switchMode('register')"
        >
          首次注册
        </button>
      </div>

      <div class="auth-heading">
        <h2>{{ title }}</h2>
        <p>{{ subtitle }}</p>
      </div>

      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        show-icon
        :closable="false"
        class="auth-error"
      />

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @submit.prevent="submit"
      >
        <el-form-item label="所属部门" prop="department_id">
          <el-select
            v-model="form.department_id"
            :loading="departmentsLoading"
            placeholder="请选择所属部门"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="department in departments"
              :key="department.id"
              :label="department.name"
              :value="department.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" :prefix-icon="User" maxlength="50" autocomplete="username" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item :label="credentialLabel" prop="credential">
          <el-input
            v-model="form.credential"
            :prefix-icon="Lock"
            type="password"
            show-password
            :autocomplete="isLogin ? 'current-password' : 'one-time-code'"
            :placeholder="credentialPlaceholder"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button
          type="primary"
          :loading="submitting"
          :icon="Right"
          class="auth-submit"
          @click="submit"
        >
          {{ isLogin ? '登录' : '完成注册' }}
        </el-button>
      </el-form>

      <p class="auth-help">
        {{ isLogin ? '首次使用？请切换到“首次注册”并填写邀请码。' : '注册成功后，后续使用公司统一密码登录。' }}
      </p>
    </div>
  </AuthLayout>
</template>
