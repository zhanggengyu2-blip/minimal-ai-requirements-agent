"""Controlled HTTP fixture for browser/integration tests. NOT a real LLM or application demo mode.
Start manually on an isolated test database; never use for claims of autonomous model quality.
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class Fixture(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path.endswith('/embeddings'):
            result={'data':[{'index':i,'embedding':[1.,0.,.5]} for i,_ in enumerate(body['input'])]}
        elif self.path.endswith('/rerank'):
            result={'results':[{'index':i,'relevance_score':.95-i*.01} for i,_ in enumerate(body['documents'])]}
        else:
            messages=body['messages'];system=messages[0]['content']
            if '需求分析工作流' in system:
                content={'standard_content':'自动识别超时未发货订单并跟踪仓储处理','business_goal':'减少履约延误并提升协作效率','type':'NEW_FEATURE','priority':'P1','is_fake':False,'fake_reason':'有明确业务场景与跟进价值','is_duplicate':False,'related_id':'','reference_rule':'真实用户目标与当前候选对照','analysis_summary':'受控测试响应：建议跟进履约异常，不代表真实模型分析效果。'}
                message={'role':'assistant','content':json.dumps(content,ensure_ascii=False)}
            else:
                context=json.loads(system[system.index('{"employee_id"'):]);project=context['current_project']
                outputs={}
                pending={}
                for m in messages:
                    if m['role']=='assistant':
                        for call in m.get('tool_calls',[]):pending[call['id']]=call['function']['name']
                    if m['role']=='tool':outputs[pending[m['tool_call_id']]]=json.loads(m['content'])
                goal=next(m['content'] for m in reversed(messages) if m['role']=='user')
                name=None;args={}
                if project:
                    pid=project['id']
                    if 'get_project_context' not in outputs:name='get_project_context';args={'project_id':pid}
                    elif 'search_knowledge' not in outputs:name='search_knowledge';args={'query':'订单超时未发货处理','project_id':pid}
                    elif 'list_tasks' not in outputs:name='list_tasks';args={'project_id':pid}
                    elif '留言' in goal and 'create_task_comment' not in outputs and outputs['list_tasks'].get('items'):
                        name='create_task_comment';args={'project_id':pid,'task_id':outputs['list_tasks']['items'][0]['id'],'content':'受控浏览器测试：请仓储核实订单发货时间。'}
                    elif '留言' not in goal and 'create_task' not in outputs:
                        members=outputs['get_project_context']['members']['items']
                        name='create_task';args={'project_id':pid,'name':'跟进模拟订单未发货','assignee_id':members[0]['user_id'],'description':'受控测试模型生成的建议，确认后创建真实内部任务。'}
                if name:
                    message={'role':'assistant','content':None,'tool_calls':[{'id':'fixture_'+str(len(outputs)),'type':'function','function':{'name':name,'arguments':json.dumps(args,ensure_ascii=False)}}]}
                else:
                    sources=[r['id'] for r in outputs.get('search_knowledge',{}).get('results',[])]
                    message={'role':'assistant','content':json.dumps({'answer':'受控模型测试：已查询项目、知识与任务。请检查待确认建议；模拟 ERP 数据不是真实订单。','source_ids':sources},ensure_ascii=False)}
            result={'choices':[{'message':message,'finish_reason':'tool_calls' if message.get('tool_calls') else 'stop'}],'usage':{'total_tokens':120}}
        data=json.dumps(result,ensure_ascii=False).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)

if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',8416),Fixture).serve_forever()
