<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import RequirementBoard from './RequirementBoard.vue'
import RequirementDialog from '../components/RequirementDialog.vue'
import RequirementDetail from '../components/RequirementDetail.vue'
import type { Requirement } from '../api'
import { requirementApi } from '../api'
import { useAppShell } from '../layouts/appShell'
import { useProjectAccess } from '../composables/useProjectAccess'

const route = useRoute()
const shell = useAppShell()
const access = useProjectAccess()
const projectId = computed(() => String(route.params.projectId || ''))
const activeProjects = computed(() => shell.projects.value.filter((item) => item.status === 'ACTIVE'))
const requirementDialog = ref(false)
const detailDialog = ref(false)
const detailLoading = ref(false)
const detail = ref<Requirement | null>(null)
const boardRef = ref<InstanceType<typeof RequirementBoard>>()
let detailTimer: ReturnType<typeof setTimeout> | undefined
let detailVersion = 0

watch(() => [detailDialog.value, detail.value?.id, detail.value?.analysis_status], () => {
  clearTimeout(detailTimer)
  if (!detailDialog.value || !detail.value || !['PENDING', 'ANALYZING'].includes(detail.value.analysis_status)) return
  const id = detail.value.id
  const version = detailVersion
  detailTimer = setTimeout(async () => {
    try {
      const updated = await requirementApi.detail(id)
      if (detailDialog.value && version === detailVersion) detail.value = updated
    } catch {
      // 请求层提示异常，保留最后一次已读取的需求内容。
    }
  }, 1500)
})
watch(detailDialog, (visible) => { if (!visible) ++detailVersion })
watch(projectId, () => { detailDialog.value = false })
onBeforeUnmount(() => { ++detailVersion; clearTimeout(detailTimer) })

const afterCreated = async () => {
  await Promise.all([boardRef.value?.refresh(), shell.refreshProjects()])
}
const showDetail = async (id: string) => {
  const version = ++detailVersion
  detailDialog.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const result = await requirementApi.detail(id)
    if (version === detailVersion) detail.value = result
  } finally {
    if (version === detailVersion) detailLoading.value = false
  }
}
watch(() => route.query.requirement_id, (id) => { if (typeof id === 'string') void showDetail(id) }, { immediate: true })
</script>

<template>
  <RequirementBoard
    ref="boardRef"
    :projects="shell.projects.value"
    :selected-project-id="projectId"
    :read-only="access.readOnly.value"
    @create="requirementDialog = true"
    @detail="showDetail"
  />
  <RequirementDialog
    v-model="requirementDialog"
    :projects="activeProjects"
    :default-project-id="projectId"
    @created="afterCreated"
  />
  <RequirementDetail
    v-model="detailDialog"
    :requirement="detail"
    :projects="shell.projects.value"
    :loading="detailLoading"
    :read-only="access.readOnly.value"
    @analyzed="value => { detail = value; void afterCreated() }"
  />
</template>
