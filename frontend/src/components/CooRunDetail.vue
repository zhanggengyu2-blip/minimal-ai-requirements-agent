<script setup lang="ts">
import { ref } from 'vue'
import { cooApi, type CooRun } from '../api/coo'
const props=defineProps<{run:CooRun}>()
const emit=defineEmits<{changed:[run:CooRun]}>()
const busy=ref(false),error=ref('')
const labels: Record<string,string>={list_projects:'查询项目',get_project_context:'查看项目与成员',list_requirements:'查询需求',get_requirement:'查看需求',analyze_requirement:'分析需求',list_tasks:'查询任务',get_task:'查看任务',list_task_comments:'查看留言',create_task_comment:'Coo 留言',create_task:'创建任务',search_knowledge:'检索知识'}
const decide=async(id:string,decision:'APPROVE'|'REJECT')=>{if(busy.value)return;busy.value=true;error.value='';try{emit('changed',await cooApi.decide(id,decision))}catch(e){error.value=e instanceof Error?e.message:'确认失败'}finally{busy.value=false}}
</script>
<template>
 <article class="coo-run">
  <header><strong>Coo · AI 同事</strong><el-tag size="small" :type="run.status==='FAILED'?'danger':run.status==='SUCCEEDED'?'success':'info'">{{run.status==='FAILED'?'执行失败':run.status==='SUCCEEDED'?'已完成调查':'执行中'}}</el-tag><small>{{new Date(run.created_time).toLocaleString()}}</small></header>
  <p class="answer" v-if="run.answer">{{run.answer}}</p>
  <el-alert v-if="run.error" :title="run.error" type="error" :closable="false"/>
  <section v-for="source in run.sources" :key="source.id" class="source"><strong>来源：{{source.document_title}} · v{{source.version}}</strong><p>{{source.content}}</p></section>
  <el-collapse v-if="run.tools.length"><el-collapse-item title="查看工具执行过程" name="tools"><div v-for="tool in run.tools" :key="tool.id" class="tool"><strong>{{labels[tool.name]||tool.name}} · {{tool.status}}</strong><p v-if="tool.error">{{tool.error}}</p><pre>{{JSON.stringify(tool.arguments,null,2)}}</pre><details><summary>执行结果</summary><pre>{{JSON.stringify(tool.result,null,2)}}</pre></details><RouterLink v-if="tool.arguments.requirement_id && run.project_id" :to="{name:'project-requirements',params:{projectId:run.project_id},query:{requirement_id:String(tool.arguments.requirement_id)}}">打开关联需求</RouterLink><RouterLink v-if="tool.arguments.task_id && tool.arguments.project_id" :to="{name:'project-task-board',params:{projectId:String(tool.arguments.project_id)},query:{task_id:String(tool.arguments.task_id)}}">打开关联任务</RouterLink></div></el-collapse-item></el-collapse>
  <div v-for="action in run.actions" :key="action.id" class="action"><strong>{{labels[action.name]||action.name}} · {{action.status==='PENDING'?'等待你确认':action.status==='SUCCEEDED'?'已执行':action.status==='REJECTED'?'已拒绝':action.status}}</strong><p v-if="action.arguments.name">任务：{{action.arguments.name}}</p><p v-if="action.arguments.content">留言：{{action.arguments.content}}</p><p v-if="action.arguments.description">说明：{{action.arguments.description}}</p><details><summary>查看完整操作内容</summary><pre>{{JSON.stringify(action.arguments,null,2)}}</pre></details><p v-if="action.error">{{action.error}}</p><div v-if="action.status==='PENDING'"><el-button type="primary" :loading="busy" @click="decide(action.id,'APPROVE')">确认执行</el-button><el-button :disabled="busy" @click="decide(action.id,'REJECT')">拒绝</el-button></div><RouterLink v-if="action.result?.id && ['create_task','create_task_comment'].includes(action.name)" :to="{name:'project-task-board',params:{projectId:action.project_id},query:{task_id:String(action.name==='create_task'?action.result.id:action.arguments.task_id)}}">打开关联任务</RouterLink></div>
  <el-alert v-if="error" :title="error" type="error"/><footer>运行 {{run.id}} · {{run.model||'模型未配置'}} · Token {{run.token_usage??'未提供'}} · {{run.trigger}}</footer>
 </article>
</template>
<style scoped>
.coo-run{background:#fff;border:1px solid #e5e9f0;border-radius:12px;padding:20px}header{display:flex;align-items:center;gap:12px}small,footer{color:#8c97a7;font-size:12px}.answer{white-space:pre-wrap;line-height:1.8;overflow-wrap:anywhere}.action,.source{background:#f6f8fc;padding:16px;border-radius:8px;margin:12px 0}.action{border-left:3px solid #6c70e8}.source p{white-space:pre-wrap}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.tool{border-bottom:1px solid #eee;padding:12px 0}footer{margin-top:15px;overflow-wrap:anywhere}a{color:#6569df;display:inline-block;margin-top:8px}
</style>
