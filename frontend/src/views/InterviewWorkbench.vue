<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'

const asset = (name: string) => `/figma-assets/interview/${name}`

interface ProjectItem {
  id: string
  initial: string
  name: string
  count: number
  color: string
}

interface UploadItem {
  id: string
  name: string
  size: string
  thumbnail: string
  objectUrl?: string
}

const projects: ProjectItem[] = [
  { id: 'minimal-ai', initial: 'A', name: '极简 AI 需求管理', count: 24, color: '#256ff5' },
  { id: 'operations', initial: 'C', name: '客户运营平台', count: 18, color: '#56d58d' },
  { id: 'analytics', initial: 'D', name: '数据分析工具', count: 12, color: '#ffaa18' },
  { id: 'internal', initial: 'I', name: '内部协作系统', count: 9, color: '#9b5de5' },
]

const query = ref('')
const activeProject = ref('minimal-ai')
const message = ref('')
const fileInput = ref<HTMLInputElement>()
const uploads = ref<UploadItem[]>([
  { id: 'design', name: '需求池页面.png', size: '286 KB', thumbnail: asset('thumbnail-blue.svg') },
  { id: 'bug', name: 'Bug复现位置.jpg', size: '512 KB', thumbnail: asset('thumbnail-orange.svg') },
])

const summary = ref([
  { label: '需求类型', value: '功能优化', pending: false },
  { label: '目标用户', value: '产品经理', pending: false },
  { label: '使用场景', value: '每周制作产品周报', pending: false },
  { label: '用户任务', value: '汇总本周需求并同步团队', pending: false },
  { label: '当前问题', value: '待补充', pending: true },
  { label: '期望结果', value: '待补充', pending: true },
])

const filteredProjects = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  return keyword ? projects.filter((item) => item.name.toLowerCase().includes(keyword)) : projects
})

const formatSize = (bytes: number) => `${Math.max(1, Math.round(bytes / 1024))} KB`

const chooseImages = () => fileInput.value?.click()

const onFilesChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  for (const file of files) {
    if (uploads.value.length >= 5) {
      ElMessage.warning('最多上传 5 张图片')
      break
    }
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
      ElMessage.warning(`${file.name} 不是支持的图片格式`)
      continue
    }
    if (file.size > 10 * 1024 * 1024) {
      ElMessage.warning(`${file.name} 超过 10MB`)
      continue
    }
    const objectUrl = URL.createObjectURL(file)
    uploads.value.push({
      id: crypto.randomUUID(),
      name: file.name,
      size: formatSize(file.size),
      thumbnail: objectUrl,
      objectUrl,
    })
  }
  input.value = ''
}

const removeImage = (id: string) => {
  const target = uploads.value.find((item) => item.id === id)
  if (target?.objectUrl) URL.revokeObjectURL(target.objectUrl)
  uploads.value = uploads.value.filter((item) => item.id !== id)
}

const sendMessage = () => {
  if (!message.value.trim() && !uploads.value.length) return
  ElMessage.success('内容已发送，等待 Agent 回复')
  message.value = ''
}

const quickAction = (type: 'unknown' | 'skip' | 'summarize') => {
  if (type === 'unknown') message.value = '这个问题我暂时不清楚。'
  if (type === 'skip') ElMessage.info('已跳过当前问题')
  if (type === 'summarize') ElMessage.success('已按当前信息开始整理需求')
}

const editSummary = (index: number) => {
  const item = summary.value[index]
  const next = window.prompt(`编辑${item.label}`, item.pending ? '' : item.value)
  if (next?.trim()) {
    item.value = next.trim()
    item.pending = false
  }
}

const exitWorkbench = () => {
  window.location.href = '/'
}

onBeforeUnmount(() => {
  uploads.value.forEach((item) => item.objectUrl && URL.revokeObjectURL(item.objectUrl))
})
</script>

<template>
  <div class="interview-workbench">
    <header class="workbench-topbar">
      <img class="workbench-logo" :src="asset('logo.svg')" alt="" />
      <h1>需求访谈工作台</h1>
      <i class="topbar-divider" />
      <div class="autosave"><img :src="asset('saved.svg')" alt="" />已自动保存</div>
      <button class="exit-workbench" type="button" @click="exitWorkbench">
        <img :src="asset('exit.svg')" alt="" />退出工作台
      </button>
      <button class="close-workbench" type="button" aria-label="关闭" @click="exitWorkbench">×</button>
    </header>

    <aside class="project-sidebar">
      <h2>选择项目</h2>
      <label class="project-search">
        <img :src="asset('search.svg')" alt="" />
        <input v-model="query" placeholder="搜索项目" />
      </label>
      <nav class="project-list">
        <button
          v-for="project in filteredProjects"
          :key="project.id"
          type="button"
          class="project-item"
          :class="{ active: activeProject === project.id }"
          @click="activeProject = project.id"
        >
          <span class="project-avatar" :style="{ background: project.color }">{{ project.initial }}</span>
          <strong>{{ project.name }}</strong>
          <em>{{ project.count }}</em>
        </button>
      </nav>
      <div class="profile-bar">
        <img :src="asset('profile.svg')" alt="张三" />
        <span>张三</span>
        <b>⌄</b>
      </div>
    </aside>

    <main class="conversation-panel">
      <section class="conversation-header">
        <div>
          <h2>极简 AI 需求管理</h2>
          <p>AI 将通过对话帮你把想法整理成清晰需求</p>
        </div>
        <div class="round-progress">
          <span>第 2 轮 · 最多 4 轮</span>
          <div><i class="current" /><i /><i /><i /></div>
        </div>
      </section>

      <section class="conversation-content">
        <div class="message-history">
          <div class="message user-message first-user">
            <time>10:23</time>
            <div class="message-row"><div class="bubble">我希望需求池可以支持批量导出。</div><img :src="asset('user-avatar.svg')" alt="用户" /></div>
          </div>
          <div class="message agent-message first-agent">
            <time>10:23</time>
            <div class="message-row"><img :src="asset('agent-avatar.svg')" alt="Agent" /><div class="bubble">明白。你通常在什么情况下需要导出这些需求？</div></div>
          </div>
          <div class="message user-message second-user">
            <time>10:24</time>
            <div class="message-row"><div class="bubble">每周做产品周报时，需要把本周需求整理给研发和管理层。</div><img :src="asset('user-avatar.svg')" alt="用户" /></div>
            <div class="sent-image">
              <img :src="asset('thumbnail-blue.svg')" alt="周报页面" />
              <div><strong>周报页面.png</strong><span>已发送 · 286 KB</span></div>
            </div>
          </div>
          <div class="message agent-message second-agent">
            <time>10:24</time>
            <div class="message-row"><img :src="asset('agent-avatar.svg')" alt="Agent" /><div class="bubble">目前整理周报时，具体遇到了什么困难？</div></div>
          </div>
        </div>

        <div class="conversation-footer">
          <div class="quick-actions">
            <button type="button" @click="quickAction('unknown')"><img :src="asset('quick-action.svg')" alt="" />不清楚</button>
            <button type="button" @click="quickAction('skip')"><img :src="asset('quick-action.svg')" alt="" />跳过这个问题</button>
            <button type="button" @click="quickAction('summarize')"><img :src="asset('quick-action.svg')" alt="" />直接整理</button>
          </div>

          <div class="message-composer" :class="{ empty: !uploads.length }">
            <div v-if="uploads.length" class="upload-list">
              <div v-for="item in uploads" :key="item.id" class="upload-card">
                <img class="upload-thumbnail" :src="item.thumbnail" :alt="item.name" />
                <div class="upload-info"><strong>{{ item.name }}</strong><span>{{ item.size }}</span></div>
                <button type="button" aria-label="删除图片" @click="removeImage(item.id)">×</button>
                <span class="upload-success">完成<i /></span>
              </div>
              <span class="upload-count">{{ uploads.length }} / 5</span>
            </div>
            <textarea v-model="message" aria-label="补充图片说明" placeholder="补充图片说明（可选）…" />
            <div class="composer-footer">
              <button class="attachment-button" type="button" aria-label="上传图片" @click="chooseImages"><img :src="asset('attachment.svg')" alt="" /></button>
              <span>支持 PNG / JPG / WEBP · 单张 ≤ 10MB</span>
              <button class="send-button" type="button" aria-label="发送" @click="sendMessage"><img :src="asset('send.svg')" alt="" /></button>
            </div>
            <input ref="fileInput" hidden type="file" accept="image/png,image/jpeg,image/webp" multiple @change="onFilesChange" />
          </div>
        </div>
      </section>
    </main>

    <aside class="summary-panel">
      <div class="summary-heading">
        <h2>需求总结</h2>
        <span><img :src="asset('live-dot.svg')" alt="" />实时更新</span>
      </div>
      <div class="summary-card">
        <div v-for="(item, index) in summary" :key="item.label" class="summary-row">
          <label>{{ item.label }}</label>
          <span :class="{ pending: item.pending }">{{ item.value }}</span>
          <button type="button" :aria-label="`编辑${item.label}`" @click="editSummary(index)"><img :src="asset('edit.svg')" alt="" /></button>
        </div>
      </div>
      <div class="completion-status"><img :src="asset('check.svg')" alt="" />已了解 3 项 · 待补充 2 项</div>
      <button class="submit-requirement" type="button" disabled>信息整理完成后可提交</button>
      <button class="save-exit" type="button" @click="exitWorkbench">暂存并退出</button>
    </aside>
  </div>
</template>

<style scoped>
.interview-workbench {
  --line: #d8e0ec;
  --text: #111827;
  width: 100vw;
  min-width: 1180px;
  height: 100vh;
  min-height: 760px;
  display: grid;
  grid-template-columns: 17% 57% 26%;
  grid-template-rows: 76px minmax(0, 1fr);
  color: var(--text);
  background: #fff;
  overflow: hidden;
}

button, input, textarea { font: inherit; }
button { border: 0; background: none; cursor: pointer; }
.workbench-topbar { grid-column: 1 / 4; display: flex; align-items: center; height: 76px; padding: 0 28px; border-bottom: 1px solid var(--line); background: #fff; }
.workbench-logo { width: 34px; height: 34px; }
.workbench-topbar h1 { margin: 0 0 0 28px; font-size: 23px; line-height: 35px; font-weight: 600; }
.topbar-divider { width: 1px; height: 28px; margin-left: 52px; background: #e4e7ec; }
.autosave { display: flex; align-items: center; gap: 8px; margin-left: 22px; color: #344054; font-size: 16px; }
.autosave img { width: 20px; height: 20px; }
.exit-workbench { display: flex; align-items: center; gap: 8px; margin-left: auto; color: #344054; font-size: 16px; }
.exit-workbench img { width: 21px; height: 21px; }
.close-workbench { margin-left: 28px; padding: 0; color: #344054; font-size: 28px; line-height: 42px; }

.project-sidebar { grid-column: 1; grid-row: 2; position: relative; min-height: 0; padding: 34px 14px 104px; color: #fff; background: linear-gradient(180deg, #001d42 0%, #00346b 100%); overflow: hidden; }
.project-sidebar h2 { margin: 0 14px 22px; font-size: 18px; line-height: 28px; font-weight: 600; }
.project-search { height: 50px; margin: 0 8px 16px; display: flex; align-items: center; border: 1px solid #4e6f94; border-radius: 9px; }
.project-search img { width: 23px; height: 23px; margin-left: 15px; }
.project-search input { min-width: 0; flex: 1; height: 100%; padding: 0 13px; color: #fff; background: transparent; border: 0; outline: none; font-size: 14px; }
.project-search input::placeholder { color: #c8d4e2; }
.project-list { display: flex; flex-direction: column; gap: 8px; }
.project-item { width: 100%; height: 64px; padding: 10px 14px; display: flex; align-items: center; gap: 12px; border-radius: 12px; color: #fff; text-align: left; }
.project-item:hover, .project-item.active { background: #164575; }
.project-avatar { width: 40px; height: 40px; flex: 0 0 40px; display: grid; place-items: center; border-radius: 50%; font-size: 15px; font-weight: 600; }
.project-item strong { min-width: 0; flex: 1; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-size: 14px; font-weight: 600; }
.project-item em { width: 28px; height: 28px; display: grid; place-items: center; border-radius: 50%; background: #256ff5; font-size: 12px; font-style: normal; }
.profile-bar { position: absolute; left: 0; right: 0; bottom: 0; height: 106px; display: flex; align-items: center; padding: 0 28px; border-top: 1px solid #315477; }
.profile-bar img { width: 48px; height: 48px; }
.profile-bar span { margin-left: 16px; font-size: 14px; }
.profile-bar b { margin-left: auto; font-size: 22px; font-weight: 400; }

.conversation-panel { grid-column: 2; grid-row: 2; min-width: 0; min-height: 0; display: flex; flex-direction: column; background: #fff; }
.conversation-header { height: 82px; flex: 0 0 82px; display: flex; justify-content: space-between; padding: 12px 30px 0; border-bottom: 1px solid #e4e7ec; }
.conversation-header h2 { margin: 0; font-size: 20px; line-height: 30px; font-weight: 600; }
.conversation-header p { margin: 1px 0 0; color: #667085; font-size: 14px; line-height: 21px; }
.round-progress { width: 160px; padding-top: 1px; color: #344054; font-size: 14px; }
.round-progress > div { display: flex; gap: 8px; margin-top: 10px; }
.round-progress i { width: 34px; height: 8px; border-radius: 4px; background: #e6ebf2; }
.round-progress i.current { background: #256ff5; }
.conversation-content { min-height: 0; flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.message-history { position: relative; min-height: 0; flex: 1; overflow-x: hidden; overflow-y: auto; scrollbar-gutter: stable; }
.message-history::-webkit-scrollbar { width: 6px; }
.message-history::-webkit-scrollbar-thumb { border-radius: 6px; background: #d8e0ec; }
.message-history::-webkit-scrollbar-track { background: transparent; }
.message { position: absolute; }
.message time { display: block; margin-bottom: 6px; color: #667085; font-size: 14px; line-height: 21px; }
.message-row { display: flex; align-items: center; gap: 14px; }
.message-row > img { width: 52px; height: 52px; flex: 0 0 52px; }
.bubble { min-height: 64px; display: flex; align-items: center; padding: 16px 20px; border-radius: 10px; font-size: 16px; line-height: 24px; }
.user-message time { text-align: right; padding-right: 94px; }
.user-message .bubble { background: #eaf2ff; }
.agent-message time { padding-left: 76px; }
.agent-message .bubble { background: #f3f4f6; }
.first-user { top: 34px; right: 40px; }
.first-user .bubble { width: 336px; }
.first-agent { top: 158px; left: 30px; }
.first-agent .bubble { width: 454px; }
.second-user { top: 282px; right: 40px; }
.second-user .bubble { width: 326px; }
.second-agent { top: 432px; left: 30px; }
.second-agent .bubble { width: 384px; }
.sent-image { position: absolute; right: 66px; top: 96px; width: 176px; height: 46px; display: flex; align-items: center; gap: 8px; padding: 5px; border: 1px solid #d7e0ed; border-radius: 8px; background: #f8fafd; }
.sent-image > img { width: 46px; height: 34px; object-fit: cover; border-radius: 5px; }
.sent-image div { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.sent-image strong { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; color: #344054; font-size: 11px; font-weight: 500; }
.sent-image span { color: #20b26b; font-size: 10px; }
.conversation-footer { position: relative; flex: 0 0 258px; border-top: 1px solid #f2f4f7; background: #fff; }
.quick-actions { position: absolute; left: 30px; top: 0; display: flex; gap: 10px; }
.quick-actions button { height: 44px; display: flex; align-items: center; gap: 8px; padding: 0 16px; border: 1px solid #d8e0ec; border-radius: 8px; color: #475467; background: #fff; font-size: 14px; }
.quick-actions button:hover { border-color: #8eb8ff; color: #256ff5; }
.quick-actions img { width: 18px; height: 18px; }
.message-composer { position: absolute; left: 30px; right: 32px; top: 62px; height: 174px; border: 1px solid #d8e0ec; border-radius: 12px; background: #fff; overflow: hidden; }
.upload-list { position: absolute; left: 18px; right: 14px; top: 14px; height: 62px; display: flex; gap: 10px; align-items: flex-start; }
.upload-card { position: relative; width: 178px; height: 62px; flex: 0 0 178px; display: flex; align-items: center; padding: 8px; border: 1px solid #d7e0ed; border-radius: 8px; background: #f8fafd; }
.upload-thumbnail { width: 46px; height: 46px; object-fit: cover; border-radius: 6px; }
.upload-info { min-width: 0; margin-left: 8px; display: flex; flex-direction: column; gap: 8px; }
.upload-info strong { width: 96px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; color: #172033; font-size: 12px; font-weight: 500; }
.upload-info span { color: #7a8699; font-size: 11px; }
.upload-card > button { position: absolute; right: 7px; top: 4px; padding: 0; color: #7a8699; font-size: 16px; }
.upload-success { position: absolute; right: 15px; bottom: 8px; display: flex; align-items: center; gap: 4px; color: #20b26b; font-size: 10px; }
.upload-success i { width: 8px; height: 8px; border-radius: 50%; background: #20b26b; }
.upload-count { margin-left: auto; padding: 20px 90px 0 0; color: #7a8699; font-size: 12px; white-space: nowrap; }
.message-composer textarea { position: absolute; left: 17px; right: 17px; top: 84px; height: 33px; resize: none; padding: 0; border: 0; outline: none; color: #344054; font-size: 16px; line-height: 24px; }
.message-composer.empty textarea { top: 18px; height: 96px; }
.message-composer textarea::placeholder { color: #98a2b3; }
.composer-footer { position: absolute; left: 21px; right: 4px; bottom: 14px; height: 44px; display: flex; align-items: center; }
.attachment-button { width: 22px; height: 22px; padding: 0; }
.attachment-button img { width: 22px; height: 22px; }
.composer-footer > span { margin-left: 8px; color: #7a8699; font-size: 12px; }
.send-button { width: 56px; height: 44px; margin-left: auto; display: grid; place-items: center; border-radius: 9px; background: #256ff5; }
.send-button:hover { background: #175fe5; }
.send-button img { width: 22px; height: 22px; }

.summary-panel { grid-column: 3; grid-row: 2; position: relative; min-width: 0; min-height: 0; padding: 24px 22px; border-left: 1px solid #e4e7ec; background: #fff; overflow: hidden; }
.summary-heading { height: 64px; display: flex; justify-content: space-between; align-items: flex-start; padding: 0 2px 0 10px; }
.summary-heading h2 { margin: 7px 0 0; font-size: 20px; line-height: 31px; font-weight: 600; }
.summary-heading > span { height: 34px; display: flex; align-items: center; gap: 7px; padding: 0 13px; border-radius: 18px; color: #259f63; background: #eef9f3; font-size: 13px; }
.summary-heading img { width: 9px; height: 9px; }
.summary-card { height: 538px; border: 1px solid #d8e0ec; border-radius: 10px; padding: 10px 24px; background: #fff; overflow: hidden; }
.summary-row { height: 86px; display: grid; grid-template-columns: 104px minmax(0, 1fr) 20px; gap: 16px; align-items: center; border-bottom: 1px solid #e4e7ec; }
.summary-row:last-child { border-bottom: 0; }
.summary-row label, .summary-row span { font-size: 14px; line-height: 22px; }
.summary-row label { color: #344054; }
.summary-row span { min-width: 0; color: #111827; }
.summary-row span.pending { color: #256ff5; }
.summary-row button { width: 20px; height: 20px; padding: 0; }
.summary-row button img { width: 20px; height: 20px; }
.completion-status { height: 60px; display: flex; align-items: center; gap: 15px; margin-top: 22px; padding: 0 18px; border: 1px solid #c9e8d7; border-radius: 10px; color: #287a50; background: #eef9f3; font-size: 14px; }
.completion-status img { width: 23px; height: 23px; }
.submit-requirement { position: absolute; left: 22px; right: 22px; bottom: 102px; height: 58px; border-radius: 10px; color: #a5adba; background: #e3e7ed; font-size: 14px; cursor: not-allowed; }
.save-exit { position: absolute; left: 50%; bottom: 47px; transform: translateX(-50%); color: #475467; font-size: 14px; }

@media (max-height: 900px) {
  .summary-panel { overflow-y: auto; }
  .submit-requirement, .save-exit { position: static; width: 100%; transform: none; margin-top: 22px; }
  .save-exit { height: 48px; }
}
</style>
