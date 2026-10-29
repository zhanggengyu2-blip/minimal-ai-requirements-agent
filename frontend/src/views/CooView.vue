<script setup lang="ts">
import { onMounted, ref, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppShell } from '../layouts/appShell'
import { cooApi, type CooRun, type CooSession } from '../api/coo'
import CooRunDetail from '../components/CooRunDetail.vue'
const route=useRoute(),shell=useAppShell()
const sessions=ref<CooSession[]>([]),active=ref<CooSession|null>(null),runs=ref<CooRun[]>([])
const projectId=ref(String(route.query.project_id||'')),content=ref(''),allowComments=ref(false),busy=ref(false),error=ref(''),configured=ref(true)
let timer:ReturnType<typeof setInterval>|undefined
const loadSessions=async()=>{sessions.value=await cooApi.sessions()}
const open=async(session:CooSession)=>{if(busy.value)return;error.value='';try{const data=await cooApi.history(session.id);active.value=data.session;projectId.value=data.session.project_id||'';runs.value=data.runs}catch(e){error.value=e instanceof Error?e.message:'读取会话失败'}}
const create=async()=>{const session=await cooApi.create(projectId.value||null);active.value=session;runs.value=[];await loadSessions()}
const send=async()=>{if(!content.value.trim()||busy.value)return;const text=content.value;busy.value=true;error.value='';try{if(!active.value)await create();content.value='';const run=await cooApi.send(active.value!.id,text,allowComments.value);runs.value.push(run);allowComments.value=false;await loadSessions()}catch(e){content.value=text;error.value=e instanceof Error?e.message:'执行失败，请刷新会话查看记录'}finally{busy.value=false}}
const update=(run:CooRun)=>{const index=runs.value.findIndex(v=>v.id===run.id);if(index>=0)runs.value[index]=run}
onMounted(async()=>{try{configured.value=(await cooApi.status()).model_configured;await loadSessions();if(sessions.value.length && !projectId.value)await open(sessions.value[0]!)}catch{error.value='Coo 加载失败'}
 timer=setInterval(()=>{if(active.value&&!busy.value&&runs.value.some(r=>r.status==='RUNNING'))void cooApi.history(active.value.id).then(d=>{runs.value=d.runs}).catch(()=>{})},4000)})
onUnmounted(()=>{if(timer)clearInterval(timer)})
</script>
<template>
 <div class="coo-page"><aside><h2>Coo</h2><p>企业 AI 同事</p><el-select v-model="projectId" clearable placeholder="企业范围" :disabled="busy||!!active"><el-option v-for="project in shell.projects.value" :key="project.id" :label="project.name" :value="project.id"/></el-select><el-button :disabled="busy" @click="active=null;runs=[];content='';error=''">新会话</el-button><button v-for="session in sessions" :key="session.id" class="session" :class="{selected:active?.id===session.id}" :disabled="busy" @click="open(session)">{{session.title}}<small>{{shell.projects.value.find(p=>p.id===session.project_id)?.name||'企业范围'}} · {{new Date(session.created_time).toLocaleDateString()}}</small></button></aside>
 <main><div class="heading"><div><h2>和 Coo 一起推进工作</h2><p>会话仅你可见。业务查询使用你的权限，写入建议由你确认。</p></div><RouterLink :to="{name:'coo-events'}">主动工作与事件</RouterLink></div><el-alert v-if="!configured" title="模型尚未配置：请在服务端设置 COO_API_KEY、COO_BASE_URL、COO_MODEL 后重启。当前没有规则演示替代模式。" type="warning" :closable="false"/><el-alert v-if="error" :title="error" type="error"/><div class="conversation"><div v-if="!runs.length" class="welcome"><h3>从一个具体目标开始</h3><p>例如：调查当前项目的履约风险，查找处理规范，并建议创建跟进任务。</p></div><div v-for="run in runs" :key="run.id" class="turn"><div class="user-message">{{run.goal}}</div><CooRunDetail :run="run" @changed="update"/></div><div v-if="busy" class="working">Coo 正在理解目标、查询业务并整理结果…</div></div><div class="composer"><el-input v-model="content" type="textarea" :rows="3" maxlength="6000" placeholder="告诉 Coo 你希望完成的工作…" :disabled="busy"/><div><el-checkbox v-model="allowComments" :disabled="busy">本轮允许 Coo 在当前授权范围内自动留言</el-checkbox><el-button type="primary" :loading="busy" :disabled="!content.trim()" @click="send">发送目标</el-button></div></div></main></div>
</template>
<style scoped>
.coo-page{display:grid;grid-template-columns:240px minmax(0,1fr);min-height:calc(100vh - 76px);background:#f8f9fc}aside{padding:24px 16px;border-right:1px solid #e7eaf1;background:#fff}aside>p{color:#8992a3}aside>.el-button{margin:16px 0}.session{display:block;border:0;background:transparent;width:100%;text-align:left;padding:12px;border-radius:8px;cursor:pointer}.session.selected{background:#eef0ff;color:#565acc}small{display:block;color:#9098a8;margin-top:6px}main{padding:28px;max-width:1100px;width:100%;box-sizing:border-box;margin:auto}.heading{display:flex;justify-content:space-between;align-items:center}.heading p{color:#8a94a5}.conversation{min-height:320px}.welcome{padding:60px 20px;color:#8792a5;text-align:center}.turn{margin:24px 0}.user-message{padding:14px 20px;margin:0 0 12px 70px;border-radius:12px;background:#ebeefe;white-space:pre-wrap;overflow-wrap:anywhere}.composer{background:white;border:1px solid #e5e9f1;padding:16px;border-radius:12px}.composer>div:last-child{display:flex;justify-content:space-between;align-items:center}.working{padding:20px;color:#6669d6}a{color:#6266d7}@media(max-width:900px){.coo-page{grid-template-columns:180px minmax(0,1fr)}main{padding:16px}}
</style>
