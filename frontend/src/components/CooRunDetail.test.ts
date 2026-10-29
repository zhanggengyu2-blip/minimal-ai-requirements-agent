import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import ElementPlus from 'element-plus'
import CooRunDetail from './CooRunDetail.vue'
import { cooApi, type CooRun } from '../api/coo'
vi.mock('../api/coo',()=>({cooApi:{decide:vi.fn()}}))
describe('Coo execution confirmation',()=>{
 it('renders the concrete proposal and executes only after the user confirms',async()=>{
  const run={id:'r',project_id:'p',goal:'调查',trigger:'CHAT',status:'SUCCEEDED',answer:'建议创建跟进任务，等待确认',error:null,tools:[],sources:[],actions:[{id:'a',project_id:'p',name:'create_task',status:'PENDING',arguments:{name:'调查未发货订单',assignee_id:'u'},result:null,error:null}],created_time:'2026-10-29T00:00:00Z',token_usage:100,model:'test'} as unknown as CooRun
  vi.mocked(cooApi.decide).mockResolvedValue({...run,actions:[]})
  const w=mount(CooRunDetail,{props:{run},global:{plugins:[ElementPlus],stubs:{RouterLink:true}}})
  expect(w.text()).toContain('调查未发货订单')
  expect(cooApi.decide).not.toHaveBeenCalled()
  await w.findAll('button').find(b=>b.text()==='确认执行')!.trigger('click');await flushPromises()
  expect(cooApi.decide).toHaveBeenCalledWith('a','APPROVE')
  expect(w.emitted('changed')).toHaveLength(1)
  w.unmount()
 })
})
