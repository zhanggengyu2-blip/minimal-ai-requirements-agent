<script setup lang="ts">
import { WarningFilled } from '@element-plus/icons-vue'
</script>

<template>
  <main class="page not-found-page">
    <el-icon :size="52"><WarningFilled /></el-icon>
    <h1>页面或项目不存在</h1>
    <p>你访问的内容不存在，或当前账号无权查看该项目。</p>
    <RouterLink class="not-found-action" :to="{ name: 'projects' }">返回项目管理</RouterLink>
  </main>
</template>
