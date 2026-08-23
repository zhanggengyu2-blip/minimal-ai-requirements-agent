<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import InterviewRecords from './InterviewRecords.vue'
import { useAppShell } from '../layouts/appShell'

const route = useRoute()
const shell = useAppShell()
const projectId = computed(() => String(route.params.projectId || ''))
</script>

<template>
  <InterviewRecords :projects="shell.projects.value" :selected-project-id="projectId" />
</template>
