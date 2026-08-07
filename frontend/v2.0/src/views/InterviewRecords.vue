<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Calendar, Close, InfoFilled, Picture, Search } from '@element-plus/icons-vue'
import type { InterviewSession, Project, Requirement, RequirementType } from '../api'
import { requirementApi } from '../api'
import { formatDate, REQUIREMENT_TYPE, shortId } from '../constants'

const props = defineProps<{ projects: Project[]; selectedProjectId?: string }>()

interface InterviewRecord {
  requirement: Requirement
  session?: InterviewSession
}

const loading = ref(false)
const detailLoading = ref(false)
const records = ref<InterviewRecord[]>([])
const activeRecord = ref<InterviewRecord>()
const drawer = ref<'dialogue' | 'summary'>()
const query = reactive<{ keyword: string; type?: RequirementType; date?: string }>({ keyword: '' })

const filteredRecords = computed(() => {
  const keyword = query.keyword.trim().toLowerCase()
  return records.value.filter(({ requirement, session }) => {
    const firstMessage = session?.messages.find((item) => item.role === 'USER')?.content || requirement.raw_content
    const submitter = session?.created_by || '未知用户'
    const matchesKeyword = !keyword || [shortId(requirement.id), submitter, firstMessage]
      .some((value) => value.toLowerCase().includes(keyword))
    const matchesType = !query.type || requirement.type === query.type
    const matchesDate = !query.date || (session?.created_time || requirement.created_time).slice(0, 10) === query.date
    return matchesKeyword && matchesType && matchesDate
  })
})

const summaryFields = computed(() => {
  const session = activeRecord.value?.session
  const card = session?.current_card || {}
  const value = (key: string) => card[key]?.value || '待补充'
  return [
    ['目标用户', value('target_user')],
    ['使用场景', value('usage_scenario')],
    ['用户任务', value('user_goal')],
    ['当前问题', value('current_problem')],
    ['用户提出的方案', value('proposed_solution')],
    ['期望结果', value('expected_result')],
    ['发生频率', value('frequency')],
    ['影响范围', value('impact_scope')],
  ]
})

const firstUserMessage = (record: InterviewRecord) =>
  record.session?.messages.find((item) => item.role === 'USER')?.content || record.requirement.raw_content

const load = async () => {
  if (!props.selectedProjectId) {
    records.value = []
    return
  }
  loading.value = true
  try {
    const data = await requirementApi.list({ project_id: props.selectedProjectId, page: 1, page_size: 100 })
    const requirements = data.items.filter((item) => item.interview_session_id)
    records.value = await Promise.all(requirements.map(async (requirement) => {
      try {
        return { requirement, session: await requirementApi.interview(requirement.id) }
      } catch {
        return { requirement }
      }
    }))
  } finally {
    loading.value = false
  }
}

const openDrawer = async (record: InterviewRecord, mode: 'dialogue' | 'summary') => {
  activeRecord.value = record
  drawer.value = mode
  if (record.session) return
  detailLoading.value = true
  try {
    record.session = await requirementApi.interview(record.requirement.id)
  } finally {
    detailLoading.value = false
  }
}

const reset = () => {
  query.keyword = ''
  query.type = undefined
  query.date = undefined
}

const attachmentUrl = (url: string) => {
  if (/^https?:\/\//.test(url)) return url
  const base = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '')
  return `${base}${url.startsWith('/') ? '' : '/'}${url.replace(/^\/api\/v1\//, '')}`
}

watch(() => props.selectedProjectId, load)
onMounted(load)
</script>

<template>
  <section class="interview-records-workspace" :class="{ 'drawer-open': drawer }">
    <main class="page interview-records-page">
      <div class="interview-page-heading">
        <h1>访谈记录</h1>
        <p>查看需求访谈记录与沟通内容</p>
      </div>

      <div class="interview-filters">
        <el-input v-model="query.keyword" :prefix-icon="Search" clearable placeholder="搜索需求编号、提交人或访谈内容" />
        <el-select v-model="query.type" clearable placeholder="全部需求类型">
          <el-option label="新增功能" value="NEW_FEATURE" />
          <el-option label="报错" value="BUG" />
          <el-option label="体验优化" value="OPTIMIZATION" />
        </el-select>
        <el-date-picker v-model="query.date" type="date" value-format="YYYY-MM-DD" placeholder="访谈日期" :prefix-icon="Calendar" />
        <el-button @click="reset">重置</el-button>
        <el-button type="primary">查询</el-button>
      </div>

      <div v-loading="loading" class="interview-table-card">
        <table class="interview-table">
          <colgroup>
            <col class="column-id" />
            <col class="column-submitter" />
            <col class="column-type" />
            <col class="column-date" />
            <col class="column-content" />
            <col class="column-actions" />
          </colgroup>
          <thead>
            <tr>
              <th>需求编号</th>
              <th>提交人</th>
              <th>需求类型</th>
              <th>访谈时间</th>
              <th>访谈内容</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody v-if="filteredRecords.length">
            <tr v-for="record in filteredRecords" :key="record.requirement.id">
              <td><span class="record-id">{{ shortId(record.requirement.id) }}</span></td>
              <td><span class="single-line">{{ record.session?.created_by || '未知用户' }}</span></td>
              <td>
                <el-tag
                  v-if="record.requirement.type"
                  :class="`interview-type ${record.requirement.type.toLowerCase()}`"
                  effect="light"
                >
                  {{ REQUIREMENT_TYPE[record.requirement.type] }}
                </el-tag>
                <span v-else>待识别</span>
              </td>
              <td><time class="single-line">{{ formatDate(record.session?.created_time || record.requirement.created_time) }}</time></td>
              <td><span class="content-preview">{{ firstUserMessage(record) }}</span></td>
              <td>
                <div class="record-actions">
                  <button type="button" @click="openDrawer(record, 'dialogue')">查看对话</button>
                  <button type="button" @click="openDrawer(record, 'summary')">查看需求总结</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!loading && !filteredRecords.length" class="interview-empty">当前项目暂无访谈记录</div>
      </div>
    </main>

    <Transition name="detail-drawer">
      <aside v-if="drawer" class="interview-detail-drawer" :aria-label="drawer === 'dialogue' ? '访谈对话详情' : '需求总结详情'">
        <header class="drawer-heading">
          <strong>{{ drawer === 'dialogue' ? '访谈对话详情' : '需求总结详情' }}</strong>
          <button type="button" aria-label="关闭" @click="drawer = undefined"><el-icon><Close /></el-icon></button>
        </header>

        <div v-loading="detailLoading" class="drawer-body">
          <template v-if="drawer === 'dialogue'">
            <div v-if="activeRecord?.session?.messages.length" class="dialogue-list">
              <div
                v-for="message in activeRecord.session.messages.filter((item) => item.role !== 'SYSTEM_EVENT')"
                :key="message.id"
                class="dialogue-message"
                :class="message.role.toLowerCase()"
              >
                <div class="message-meta">
                  <span>{{ message.role === 'USER' ? (activeRecord.session.created_by || '提交人') : '需求访谈助手' }}</span>
                  <time>{{ formatDate(message.created_time) }}</time>
                </div>
                <div class="dialogue-bubble">{{ message.content }}</div>
                <a
                  v-for="attachment in message.attachments"
                  :key="attachment.id"
                  class="image-attachment"
                  :href="attachmentUrl(attachment.preview_url)"
                  target="_blank"
                >
                  <img :src="attachmentUrl(attachment.preview_url)" :alt="attachment.original_name" />
                  <span><el-icon><Picture /></el-icon>{{ attachment.original_name }}</span>
                </a>
              </div>
            </div>
            <el-empty v-else description="暂无对话内容" />
          </template>

          <template v-else>
            <h3 class="summary-title">访谈后需求总结</h3>
            <dl class="summary-detail-list">
              <div v-for="field in summaryFields" :key="field[0]">
                <dt>{{ field[0] }}</dt>
                <dd :class="{ pending: field[1] === '待补充' }">{{ field[1] }}</dd>
              </div>
            </dl>
            <p class="summary-ai-note"><el-icon><InfoFilled /></el-icon><span>以上内容由 AI 根据访谈对话整理，仅用于需求分析与回溯。</span></p>
          </template>
        </div>

        <footer class="drawer-footer"><el-button @click="drawer = undefined">关闭</el-button></footer>
      </aside>
    </Transition>
  </section>
</template>
