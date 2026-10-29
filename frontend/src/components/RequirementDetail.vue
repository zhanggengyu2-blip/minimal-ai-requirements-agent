<script setup lang="ts">
import { computed, ref } from 'vue'
import { CircleCheck, InfoFilled, Loading, Warning, MagicStick } from '@element-plus/icons-vue'
import { requirementApi, type Project, type Requirement } from '../api'
import { ANALYSIS_STATUS, PRIORITY, REQUIREMENT_TYPE, formatDate, shortId } from '../constants'

const props = defineProps<{
  modelValue: boolean
  requirement: Requirement | null
  projects: Project[]
  loading?: boolean
  readOnly?: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; analyzed: [value: Requirement] }>()
const analyzing = ref(false)
const analysisError = ref('')
const analyze = async () => {
  if (!props.requirement || props.readOnly || analyzing.value) return
  analyzing.value = true; analysisError.value = ''
  try { emit('analyzed', await requirementApi.analyze(props.requirement.id)) }
  catch (e) { analysisError.value = e instanceof Error ? e.message : '分析失败' }
  finally { analyzing.value = false }
}
const projectName = computed(() =>
  props.projects.find((project) => project.id === props.requirement?.project_id)?.name || '未知项目',
)
const statusClass = computed(() => props.requirement?.analysis_status.toLowerCase())
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="需求详情"
    width="650px"
    class="product-dialog detail-dialog"
    @close="emit('update:modelValue', false)"
  >
    <div v-loading="loading">
      <template v-if="requirement">
        <div class="detail-grid">
          <div class="detail-box">
            <label>所属项目</label><strong>{{ projectName }}</strong>
            <label>AI 分析状态</label>
            <el-tag :class="`analysis-tag ${statusClass}`">{{ ANALYSIS_STATUS[requirement.analysis_status] }}</el-tag>
          </div>
          <div class="detail-box">
            <label>需求编号</label><strong>{{ shortId(requirement.id) }}</strong>
            <label>需求等级</label>
            <span v-if="requirement.priority" :class="`priority-badge ${requirement.priority.toLowerCase()}`">
              {{ requirement.priority }} · {{ PRIORITY[requirement.priority] }}
            </span>
            <span v-else>待分析</span>
          </div>
        </div>

        <section class="detail-section">
          <h4>原始需求描述</h4>
          <div class="content-box">{{ requirement.raw_content }}</div>
        </section>

        <section class="detail-section">
          <h4>AI 建议</h4>
          <div v-if="requirement.analysis_status === 'NOT_RUN'" class="ai-panel not-run">
            <div class="ai-title"><el-icon :size="25"><InfoFilled /></el-icon><strong>未开启 AI 分析</strong></div>
            <p>需求已保存。本次提交未开启 AI分析生成，不会执行 AI 分析任务。</p>
          </div>
          <div v-else-if="requirement.analysis_status === 'ANALYZING' || requirement.analysis_status === 'PENDING'" class="ai-panel analyzing">
            <el-icon class="spin" :size="42"><Loading /></el-icon>
            <strong>{{ requirement.analysis_status === 'PENDING' ? '等待 AI 分析' : 'AI 正在分析中' }}</strong>
            <p>需求已保存，分析结果可能有延迟，完成后将自动更新。</p>
          </div>
          <div v-else-if="requirement.analysis_status === 'FAILED'" class="ai-panel failed">
            <div class="ai-title"><el-icon :size="25"><Warning /></el-icon><strong>AI 分析失败</strong></div>
            <p class="emphasis">需求已保存，但 AI 分析失败，原始内容不会丢失。</p>
            <p>失败原因：{{ requirement.analysis_error_message || '分析服务暂时不可用' }}</p>
            <p v-if="requirement.analysis_error_code">错误代码：{{ requirement.analysis_error_code }}</p>
          </div>
          <div v-else class="ai-panel success">
            <div class="ai-title">
              <el-icon :size="26"><MagicStick /></el-icon>
              <el-tag type="success"><el-icon><CircleCheck /></el-icon> 分析完成</el-tag>
            </div>
            <div class="result-list">
              <div><label>标准化内容</label><p>{{ requirement.standard_content || '—' }}</p></div>
              <div><label>业务目标</label><p>{{ requirement.business_goal || '—' }}</p></div>
              <div class="result-pair">
                <span><label>需求类型</label>{{ requirement.type ? REQUIREMENT_TYPE[requirement.type] : '—' }}</span>
                <span><label>优先级</label>{{ requirement.priority ? `${requirement.priority} · ${PRIORITY[requirement.priority]}` : '—' }}</span>
              </div>
              <div class="result-pair">
                <span><label>真伪判断</label>{{ requirement.is_fake == null ? '—' : requirement.is_fake ? '伪需求' : '真实需求' }}</span>
                <span><label>重复判断</label>{{ requirement.is_duplicate == null ? '—' : requirement.is_duplicate ? '可能重复' : '无重复' }}</span>
              </div>
              <div v-if="requirement.fake_reason"><label>伪需求原因</label><p>{{ requirement.fake_reason }}</p></div>
              <div v-if="requirement.related_id"><label>关联需求</label><p>{{ requirement.related_id }}</p></div>
              <div v-if="requirement.reference_rule"><label>参考规则</label><p>{{ requirement.reference_rule }}</p></div>
              <div v-if="requirement.analysis_summary"><label>分析总结</label><p>{{ requirement.analysis_summary }}</p></div>
            </div>
          </div>
          <div class="ai-disclaimer"><el-icon><InfoFilled /></el-icon> AI 建议仅供参考，不会自动修改需求内容</div>
        </section>

        <div class="meta-box">
          <span><label>创建人</label>{{ requirement.created_by || '匿名用户' }}</span>
          <span><label>提交时间</label>{{ formatDate(requirement.created_time) }}</span>
          <span><label>人工修改</label>{{ requirement.manual_modify ? '是' : '否' }}</span>
        </div>
      </template>
    </div>
    <el-alert v-if="analysisError" :title="analysisError" type="error" />
    <template #footer>
      <el-button v-if="requirement && !readOnly" :loading="analyzing" :disabled="['PENDING', 'ANALYZING'].includes(requirement.analysis_status)" @click="analyze">Coo 分析需求</el-button>
      <el-button type="primary" @click="emit('update:modelValue', false)">完成</el-button>
    </template>
  </el-dialog>
</template>
