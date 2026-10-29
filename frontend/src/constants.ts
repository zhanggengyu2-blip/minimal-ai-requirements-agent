import type {
  AnalysisStatus,
  ProjectStatus,
  RequirementPriority,
  RequirementType,
  InvitationStatus,
} from './api'

export const PROJECT_STATUS: Record<ProjectStatus, string> = {
  ACTIVE: '正常项目',
  ARCHIVED: '已归档',
}

export const PRIORITY: Record<RequirementPriority, string> = {
  P0: '紧急',
  P1: '高',
  P2: '中',
  P3: '低',
}

export const REQUIREMENT_TYPE: Record<RequirementType, string> = {
  NEW_FEATURE: '新增功能',
  BUG: '报错',
  OPTIMIZATION: '体验优化',
}

export const ANALYSIS_STATUS: Record<AnalysisStatus, string> = {
  NOT_RUN: '未开启 AI 分析',
  PENDING: '等待分析',
  ANALYZING: '分析中',
  ANALYZED: '分析完成',
  FAILED: '分析失败',
}

export const INVITATION_STATUS: Record<InvitationStatus, string> = {
  UNUSED: '未使用',
  USED: '已使用',
  DISABLED: '已停用',
}

export const formatDate = (value: string) =>
  new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(value)).replaceAll('/', '-')

export const shortId = (id: string) => `REQ-${id.slice(-6).toUpperCase()}`
