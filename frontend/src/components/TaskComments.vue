<script setup lang="ts">
import { ref, watch } from 'vue'
import { commentApi, type TaskComment } from '../api/taskComments'
const props = defineProps<{projectId: string; taskId: string; readOnly?: boolean}>()
const rows = ref<TaskComment[]>([])
const content = ref('')
const replying = ref<TaskComment | null>(null)
const busy = ref(false)
const error = ref('')
const more = ref(false)
const load = async (older = false) => {
  const project = props.projectId, task = props.taskId
  try {
    const data = await commentApi.list(project, task, older ? rows.value[0]?.id : undefined)
    if (project !== props.projectId || task !== props.taskId) return
    rows.value = older ? [...data, ...rows.value] : data
    more.value = data.length === 100
  } catch { error.value = '留言加载失败，请重试' }
}
const send = async () => {
  if (!content.value.trim() || busy.value || props.readOnly) return
  busy.value = true; error.value = ''
  try { await commentApi.create(props.projectId, props.taskId, content.value.trim(), replying.value?.id || null); content.value = ''; replying.value = null; await load() }
  catch { error.value = '留言未发送，请检查权限后重试' }
  finally { busy.value = false }
}
watch(() => [props.projectId, props.taskId], () => { rows.value = []; replying.value = null; content.value = ''; error.value = ''; void load() }, { immediate: true })
</script>
<template>
  <section class="task-comments">
    <h3>任务留言</h3>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <el-button v-if="more" text @click="load(true)">加载更早留言</el-button>
    <p v-if="!rows.length">暂无留言</p>
    <article v-for="row in rows" :key="row.id" class="comment-row">
      <strong>{{ row.author_name }}</strong> <el-tag v-if="row.actor_type === 'COO'" size="small">AI</el-tag>
      <time>{{ new Date(row.created_time).toLocaleString() }}</time>
      <small v-if="row.parent_id">回复：{{ rows.find(item => item.id === row.parent_id)?.author_name || '历史留言' }}</small>
      <p>{{ row.content }}</p>
      <el-button v-if="!readOnly" text size="small" @click="replying = row">回复</el-button>
    </article>
    <template v-if="!readOnly">
      <p v-if="replying">回复 {{ replying.author_name }} <el-button text @click="replying = null">取消回复</el-button></p>
      <el-input v-model="content" type="textarea" :rows="3" maxlength="4000" show-word-limit placeholder="留言或回复，协同跟进任务" />
      <el-button type="primary" :loading="busy" :disabled="!content.trim()" @click="send">发送留言</el-button>
    </template>
  </section>
</template>
<style scoped>
.task-comments{border-top:1px solid #e4e7ed;margin-top:20px;padding-top:10px}.comment-row{padding:12px 0;border-bottom:1px solid #eee}.comment-row p{white-space:pre-wrap;overflow-wrap:anywhere}time{font-size:12px;color:#909399;margin-left:12px}small{display:block;color:#909399}.task-comments>.el-button{margin-top:12px}
</style>
