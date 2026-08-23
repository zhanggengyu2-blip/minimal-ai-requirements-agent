<script setup lang="ts">
import { computed, ref } from 'vue'
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

const afterCreated = async () => {
  await Promise.all([boardRef.value?.refresh(), shell.refreshProjects()])
}
const showDetail = async (id: string) => {
  detailDialog.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await requirementApi.detail(id)
  } finally {
    detailLoading.value = false
  }
}
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
  />
</template>
