<script setup lang="ts">
import { onMounted, ref } from 'vue'
import InvitationManagement from './InvitationManagement.vue'
import { departmentApi, type Department } from '../api'

const departments = ref<Department[]>([])
const loadDepartments = async () => {
  departments.value = (await departmentApi.list({ page: 1, page_size: 100 })).items
}
onMounted(loadDepartments)
</script>

<template>
  <InvitationManagement :departments="departments" />
</template>
