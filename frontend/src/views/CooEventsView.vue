<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { http } from '../api/http'
import { cooApi, type CooRun } from '../api/coo'
import { useAppShell } from '../layouts/appShell'
import CooRunDetail from '../components/CooRunDetail.vue'
interface BusinessEvent {id:string;project_id:string;event_type:string;origin:string;status:string;attempts:number;run_id:string|null;error:string|null;payload:Record<string,unknown>;created_time:string}
const shell=useAppShell(),events=ref<BusinessEvent[]>([]),runs=ref<CooRun[]>([]),selected=ref<CooRun|null>(null),busy=ref(false),error=ref('')
const projectId=ref(''),orderId=ref(`DEMO-${Date.now().toString().slice(-8)}`)
let timer:ReturnType<typeof setInterval>|undefined
const labels:Record<string,string>={REQUIREMENT_CREATED:'新需求',TASK_UPDATED:'任务变化',TASK_COMMENT_CREATED:'新留言',FULFILLMENT_DELAY:'履约异常'}
const load=async()=>{[events.value,runs.value]=await Promise.all([http.get<never,BusinessEvent[]>('/coo/events'),http.get<never,CooRun[]>('/coo/runs')])}
const simulate=async()=>{if(busy.value)return;busy.value=true;error.value='';try{await http.post('/coo/events/simulated-order',{project_id:projectId.value,order_id:orderId.value,hours_waiting:72,warehouse:'模拟杭州一号仓'});await load()}catch(e){error.value=e instanceof Error?e.message:'模拟失败'}finally{busy.value=false}}
const show=async(id:string)=>{try{selected.value=await cooApi.run(id)}catch(e){error.value=e instanceof Error?e.message:'加载记录失败'}}
const showRun=(row:CooRun)=>{void show(row.id)}
const retry=async(id:string)=>{try{await http.post(`/coo/events/${id}/retry`);await load()}catch(e){error.value=e instanceof Error?e.message:'重试失败'}}
onMounted(()=>{void load().catch(()=>{error.value='事件读取失败'});timer=setInterval(()=>{void load().then(()=>{if(selected.value){const next=runs.value.find(r=>r.id===selected.value?.id);if(next)selected.value=next}}).catch(()=>{})},4000)})
onUnmounted(()=>{if(timer)clearInterval(timer)})
</script>
<template>
 <div class="events-page"><div class="head"><div><h2>Coo 主动工作</h2><p>业务事件 → 自主调查 → 操作建议 → 员工确认 → 任务协作</p></div><RouterLink :to="{name:'coo'}">返回 Coo 对话</RouterLink></div><el-alert title="演示数据明确标记为模拟 ERP。本版尚未接入真实 ERPNext。事件由服务端后台进程处理，关闭浏览器后仍可执行。" type="info" :closable="false"/><el-alert v-if="error" :title="error" type="error"/>
 <section class="simulation"><strong>模拟订单超时未发货</strong><el-select v-model="projectId" placeholder="选择可写项目"><el-option v-for="p in shell.projects.value.filter(p=>p.status==='ACTIVE')" :key="p.id" :label="p.name" :value="p.id"/></el-select><el-input v-model="orderId" placeholder="模拟订单号（重复订单自动去重）"/><el-button type="primary" :loading="busy" :disabled="!projectId||!orderId" @click="simulate">保存异常事件</el-button></section>
 <h3>我的业务事件</h3><p class="hint">待处理事件需要后台进程运行；启动方式见 README。失败事件可查看原因并重试。</p><el-table :data="events"><el-table-column label="事件"><template #default="{row}">{{labels[row.event_type]||row.event_type}}<el-tag v-if="row.origin==='SIMULATED_ERP'" size="small" type="warning">模拟 ERP</el-tag></template></el-table-column><el-table-column label="项目"><template #default="{row}">{{shell.projects.value.find(p=>p.id===row.project_id)?.name||row.project_id}}</template></el-table-column><el-table-column prop="status" label="处理状态"/><el-table-column prop="attempts" label="尝试次数" width="90"/><el-table-column prop="error" label="失败原因"/><el-table-column label="操作" width="190"><template #default="{row}"><el-button v-if="row.run_id" text @click="show(row.run_id)">查看调查</el-button><el-button v-if="row.status==='FAILED'" text @click="retry(row.id)">重试</el-button></template></el-table-column></el-table>
 <h3>最近执行记录</h3><el-table :data="runs" @row-click="showRun" class="runs-table"><el-table-column prop="trigger" label="触发来源" width="190"/><el-table-column label="目标"><template #default="{row}">{{row.goal.slice(0,100)}}</template></el-table-column><el-table-column prop="status" label="执行状态" width="130"/><el-table-column label="Token" width="120"><template #default="{row}">{{row.token_usage??'未提供'}}</template></el-table-column><el-table-column label="时间" width="190"><template #default="{row}">{{new Date(row.created_time).toLocaleString()}}</template></el-table-column></el-table>
 <el-drawer :model-value="!!selected" title="Coo 执行记录与操作建议" size="720px" @close="selected=null"><CooRunDetail v-if="selected" :run="selected" @changed="run=>{selected=run;void load()}"/></el-drawer>
 </div>
</template>
<style scoped>
.events-page{padding:28px;max-width:1400px;margin:auto}.head{display:flex;justify-content:space-between;align-items:center}.head p,.hint{color:#8b95a5}.simulation{display:flex;align-items:center;gap:14px;padding:24px;background:white;border:1px solid #e6eaf2;border-radius:10px;margin-top:20px}.simulation>.el-input{max-width:300px}.simulation>.el-select{width:230px}.runs-table{cursor:pointer}h3{margin-top:28px}a{color:#6769db}
</style>
