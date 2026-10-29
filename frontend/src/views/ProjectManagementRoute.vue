<script setup lang="ts">
import { ref, watch } from 'vue'
import ProjectManagement from './ProjectManagement.vue'
import { useAppShell } from '../layouts/appShell'

const shell = useAppShell()
const projectManagement = ref<InstanceType<typeof ProjectManagement>>()
watch(shell.projectListRevision, () => { void projectManagement.value?.refresh() })
</script>

<template>
  <ProjectManagement
    ref="projectManagement"
    @create="shell.openProjectDialog"
    @changed="shell.refreshProjects"
  />
</template>
