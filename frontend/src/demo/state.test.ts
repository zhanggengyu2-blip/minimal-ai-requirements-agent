import { describe, expect, it } from 'vitest'
import { createDemoState, createDemoRun, confirmDemoProposal } from './state'
describe('isolated local demo', () => {
  it('creates a linked task only once after confirmation', () => {
    const state=createDemoState(),run=state.runs[0]!,before=state.tasks.length
    const id=confirmDemoProposal(state,run)
    expect(state.tasks).toHaveLength(before+1)
    expect(state.tasks.find(task=>task.id===id)?.fromCoo).toBe(true)
    expect(confirmDemoProposal(state,run)).toBe(id)
    expect(state.tasks).toHaveLength(before+1)
  })
  it('uses the same task for AI comments and task status updates', () => {
    const state=createDemoState(),comment=createDemoRun('comment','跟进留言')
    comment.status='done';confirmDemoProposal(state,comment)
    expect(state.tasks[0]!.comments.at(-1)?.ai).toBe(true)
    const update=createDemoRun('status','更新状态');update.status='done';update.proposal!.taskStatus='已完成'
    confirmDemoProposal(state,update)
    expect(state.tasks[0]!.status).toBe('已完成')
  })
  it('does not execute unfinished or rejected suggestions and resets independently', () => {
    const state=createDemoState(),run=createDemoRun('investigate','调查')
    confirmDemoProposal(state,run);expect(state.tasks).toHaveLength(5)
    run.status='done';run.proposal!.status='rejected';confirmDemoProposal(state,run)
    expect(state.tasks).toHaveLength(5)
    state.tasks[0]!.comments.push({id:'test',author:'林晓',ai:false,content:'本地修改',parentId:null,time:'10:00'})
    expect(createDemoState().tasks[0]!.comments).toHaveLength(2)
  })
})
