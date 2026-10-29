/** Local UI fixtures only. No API clients, model calls, auth or business persistence. */
export type DemoTab = 'coo' | 'requirements' | 'tasks' | 'knowledge' | 'versions' | 'events' | 'runs'
export type TaskStatus = '未开始' | '进行中' | '已完成'
export interface DemoComment { id: string; author: string; ai: boolean; content: string; time: string; parentId: string | null }
export interface DemoTask { id: string; name: string; assignee: string; status: TaskStatus; priority: string; description: string; due: string; comments: DemoComment[]; fromCoo?: boolean }
export interface DemoKnowledge { id: string; title: string; category: string; scope: string; version: number; published: boolean; content: string; updated: string }
export interface DemoRequirement { id: string; title: string; raw: string; status: '待分析' | '已分析'; priority: string; type: string; goal: string; summary: string }
export interface DemoStep { name: string; tool: string; detail: string; status: 'waiting' | 'running' | 'done' }
export interface DemoProposal { kind: 'task' | 'comment' | 'status'; status: 'pending' | 'accepted' | 'rejected'; title: string; assignee: string; content: string; taskId: string | null; due: string; taskStatus: TaskStatus }
export interface DemoRun { id: string; goal: string; origin: '员工对话' | '业务事件'; status: 'running' | 'done'; steps: DemoStep[]; answer: string; sourceId: string | null; proposal: DemoProposal | null; time: string }
export interface DemoEvent { id: string; order: string; title: string; status: '待处理' | '调查中' | '待确认' | '已跟进'; runId: string | null; time: string }
export interface DemoState { tasks: DemoTask[]; knowledge: DemoKnowledge[]; requirements: DemoRequirement[]; runs: DemoRun[]; events: DemoEvent[] }
export const members = ['王磊', '陈佳', '林晓']
export const statusOptions: TaskStatus[] = ['未开始', '进行中', '已完成']
export const nowLabel = () => new Date().toLocaleTimeString('zh-CN', { timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit' })
let nextId = 100
export const demoId = (prefix: string) => `${prefix}-${++nextId}`

export function createDemoRun(kind: 'investigate' | 'knowledge' | 'comment' | 'status', goal: string, origin: DemoRun['origin'] = '员工对话', order = 'DEMO-0846'): DemoRun {
  const task = { kind: 'task', status: 'pending', title: '调查订单超时未发货原因', assignee: '王磊', content: `核实订单 ${order} 在杭州一号仓的库存与拣货状态，确认预计处理时间，并在任务留言中同步进展。`, taskId: null, due: '2026-10-30', taskStatus: '未开始' } satisfies DemoProposal
  const proposal: DemoProposal | null = kind === 'knowledge' ? null : kind === 'comment' ? { ...task, kind: 'comment', title: '向仓储跟进任务留言', content: '请确认订单 DEMO-0846 的库存与拣货情况，有进展后在这里同步。', taskId: 'TASK-1024' } : kind === 'status' ? { ...task, kind: 'status', title: '更新仓储调查任务状态', taskId: 'TASK-1024', taskStatus: '进行中' } : task
  return {
    id: demoId('RUN'), goal, origin, status: 'running', time: nowLabel(), sourceId: 'KB-001', proposal,
    answer: kind === 'knowledge' ? '根据《订单超时未发货处理规范》，已付款超过 48 小时仍未发货时，应先联系仓储核实库存与拣货状态，并记录处理进展。在原因确认前，不向客户承诺具体发货时间。' : kind === 'comment' ? '已查看任务和最近留言。仓储正在核查拣货情况，我整理了一条跟进留言，确认后将以 Coo 的 AI 身份显示在任务中。' : kind === 'status' ? '任务已经有明确负责人，并开始核查仓储情况。建议把状态更新为「进行中」，方便团队在看板和版本中同步跟进。' : `订单 ${order} 已付款 72 小时，超过规范中的 48 小时跟进阈值。当前还缺少仓储侧的原因反馈。\n\n建议由王磊核实库存与拣货情况，并在明天前同步处理结论。我已准备好跟进任务，确认后会出现在团队任务中。`,
    steps: [
      { name: '了解当前项目', tool: 'get_project_context', detail: '电商履约协作 · 项目成员 3 人，王磊负责仓储协调', status: 'waiting' },
      { name: '查找处理规范', tool: 'search_knowledge', detail: '找到《订单超时未发货处理规范》v2，包含 48 小时跟进规则', status: 'waiting' },
      { name: kind === 'comment' ? '查看最近任务留言' : '查看相关跟进任务', tool: kind === 'comment' ? 'list_task_comments' : 'list_tasks', detail: '仓储协调任务已有负责人，尚未收到明确的发货时间反馈', status: 'waiting' },
      { name: kind === 'knowledge' ? '整理回答与来源' : '准备待确认的操作', tool: kind === 'knowledge' ? 'answer' : kind === 'comment' ? 'create_task_comment' : kind === 'status' ? 'update_task' : 'create_task', detail: kind === 'knowledge' ? '展示本次回答引用的知识片段' : '仅生成建议，等待员工确认', status: 'waiting' },
    ],
  }
}

export function createDemoState(): DemoState {
  const first = createDemoRun('investigate', '调查一下订单延迟发货的问题，查查处理规范，帮我安排后续跟进。')
  first.status = 'done'; first.time = '09:42'; first.steps.forEach(step => { step.status = 'done' })
  return {
    tasks: [
      { id: 'TASK-1024', name: '核查杭州仓拣货异常', assignee: '王磊', status: '进行中', priority: 'P1', description: '汇总杭州一号仓待拣货订单，核对库存与波次分配，向客服同步调查结果。', due: '2026-10-30', comments: [
        { id: 'C-1', author: '陈佳', ai: false, content: '客户已经咨询发货时间，请仓储协助核查。', time: '09:10', parentId: null },
        { id: 'C-2', author: '王磊', ai: false, content: '已联系仓库，正在核对拣货波次，上午会同步第一轮结果。', time: '09:26', parentId: 'C-1' },
      ] },
      { id: 'TASK-1025', name: '梳理超时订单提醒规则', assignee: '林晓', status: '未开始', priority: 'P1', description: '明确 48 小时提醒条件、通知对象与重复提醒策略。', due: '2026-10-31', comments: [] },
      { id: 'TASK-1026', name: '更新客服发货进度话术', assignee: '陈佳', status: '未开始', priority: 'P2', description: '仓储原因确认后，统一更新客服沟通模板。', due: '2026-11-02', comments: [] },
      { id: 'TASK-1027', name: '完成仓储联系人信息核对', assignee: '王磊', status: '已完成', priority: 'P2', description: '核对各仓联系人、工作时间及备用联系方式。', due: '2026-10-28', comments: [] },
      { id: 'TASK-1028', name: '确认履约异常协作流程', assignee: '林晓', status: '已完成', priority: 'P1', description: '确认客服发现异常、仓储调查、任务记录的协作流程。', due: '2026-10-29', comments: [] },
    ],
    knowledge: [
      { id: 'KB-001', title: '订单超时未发货处理规范', category: '履约协作', scope: '项目成员', version: 2, published: true, content: '已付款超过 48 小时未发货，应联系仓储核实库存与拣货状态。\n\n若为缺货，由采购确认补货计划；若为拣货异常，由仓储负责人协调处理。\n\n每次进展应记录在跟进任务的留言中。原因确认前，不得向客户承诺具体发货时间。', updated: '10月28日' },
      { id: 'KB-002', title: '客户沟通与服务承诺', category: '企业规范', scope: '企业全员', version: 3, published: true, content: '对客户提供经过业务负责人确认的信息。\n\n需要跨部门调查时，记录问题、责任人与下次跟进时间。避免使用无法兑现的承诺。', updated: '10月27日' },
      { id: 'KB-003', title: '杭州一号仓对接说明', category: '仓储资料', scope: '项目成员', version: 1, published: true, content: '仓储协调人：王磊。\n\n工作时间：工作日 09:00—18:00。查询前准备订单编号、付款时间与当前状态。', updated: '10月26日' },
      { id: 'KB-004', title: '异常订单复盘模板', category: '履约协作', scope: '项目成员', version: 1, published: false, content: '异常概况：\n影响范围：\n原因调查：\n处理过程：\n后续改进：', updated: '今天' },
    ],
    requirements: [
      { id: 'REQ-1041', title: '自动识别超时未发货订单', raw: '希望客服能及时发现付款超过 48 小时仍未发货的订单，通知仓储调查，并持续跟进处理进度。', status: '已分析', priority: 'P1', type: '新增功能', goal: '降低履约延误带来的咨询成本，让异常有人负责、进度可见。', summary: '用户场景与业务价值明确。建议先覆盖超时发现、责任人跟进和任务留痕三个环节。' },
      { id: 'REQ-1042', title: '任务中保留仓储反馈记录', raw: '客服和仓储的信息散落在聊天里，希望在任务中留言和回复，方便后续查找。', status: '已分析', priority: 'P1', type: '体验优化', goal: '减少跨部门信息遗漏，提高跟进效率。', summary: '建议沿用现有团队任务，增加留言、回复和明确的 AI 身份。' },
      { id: 'REQ-1043', title: '一键生成每周异常复盘', raw: '每周汇总异常订单和处理情况，生成一份复盘材料。', status: '待分析', priority: '待评估', type: '待分析', goal: '', summary: '' },
    ],
    runs: [first],
    events: [{ id: 'EVT-001', order: 'DEMO-0846', title: '订单超时未发货', status: '待处理', runId: null, time: '09:38' }],
  }
}

/** Local and idempotent: approving twice cannot duplicate a demo task/comment. */
export function confirmDemoProposal(state: DemoState, run: DemoRun): string | null {
  const p = run.proposal
  if (!p || p.status !== 'pending' || run.status !== 'done') return p?.taskId || null
  if (p.kind === 'task') {
    const task: DemoTask = { id: demoId('TASK'), name: p.title, assignee: p.assignee, status: '未开始', priority: 'P1', description: p.content, due: p.due, comments: [], fromCoo: true }
    state.tasks.unshift(task); p.taskId = task.id
  } else {
    const task = state.tasks.find(t => t.id === p.taskId)
    if (!task) return null
    if (p.kind === 'comment') task.comments.push({ id: demoId('C'), author: 'Coo', ai: true, content: p.content, time: nowLabel(), parentId: null })
    else task.status = p.taskStatus
  }
  p.status = 'accepted'
  state.events.filter(event => event.runId === run.id).forEach(event => { event.status = '已跟进' })
  return p.taskId
}
