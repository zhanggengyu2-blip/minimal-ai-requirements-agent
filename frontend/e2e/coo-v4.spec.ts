import { expect, test } from '@playwright/test'
// Requires the explicitly labelled controlled model fixture, never a paid production model.
test('V4 knowledge, Coo confirmation, AI comment and proactive event loop',async({page})=>{
 test.setTimeout(90000)
 test.skip(process.env.E2E_COO_FIXTURE !== '1','Requires isolated controlled HTTP model fixture')
 await page.goto('/login')
 await page.getByRole('combobox',{name:'所属部门'}).click();await page.getByRole('option',{name:'产品部',exact:true}).click()
 await page.getByRole('textbox',{name:'姓名'}).fill('E2E管理员');await page.getByRole('textbox',{name:'公司统一密码'}).fill('e2e-shared-password')
 await page.getByRole('button',{name:'登录',exact:true}).click();await expect(page.getByRole('heading',{name:'项目管理'})).toBeVisible()
 const auth=await (await page.request.get('http://127.0.0.1:8000/api/v1/auth/me')).json()
 const headers={'X-CSRF-Token':auth.data.csrf_token},base='http://127.0.0.1:8000/api/v1'
 const suffix=Date.now()
 const knowledgeTitle=`发货异常处理规范-${suffix}`
 const project=(await (await page.request.post(base+'/projects',{headers,data:{name:`V4浏览器验收-${suffix}`,project_context:'电商履约协作，成员负责联系仓储核查订单超时未发货。'}})).json()).data
 const cat=(await (await page.request.post(base+'/knowledge/categories',{headers,data:{name:'履约规范',scope:'PROJECT',project_id:project.id,access_policy:'PROJECT_MEMBERS'}})).json()).data
 const doc=(await (await page.request.post(base+'/knowledge/documents',{headers,data:{title:knowledgeTitle,category_id:cat.id,content:'订单已付款超过48小时未发货，联系仓储核实库存与拣货状态，在任务留言记录进展。'}})).json()).data
 const published=await page.request.post(`${base}/knowledge/documents/${doc.id}/publish`,{headers,data:{expected_revision:doc.revision}})
 expect((await published.json()).data.versions[0].status).toBe('PUBLISHED')
 await page.goto('/knowledge');await expect(page.getByText(knowledgeTitle,{exact:true})).toBeVisible()
 await page.getByPlaceholder('例如：订单超时未发货应该如何跟进？').fill('订单超时未发货')
 await page.locator('.recall .el-select').click();await page.getByRole('option',{name:project.name,exact:true}).click()
 await page.getByRole('button',{name:'测试召回'}).click();await expect(page.getByText(`${knowledgeTitle} · v1`,{exact:true})).toBeVisible()
 // The normal requirement workflow really traverses HTTP and persists the ten validated fields.
 const requirement=(await (await page.request.post(base+'/requirements',{headers,data:{project_id:project.id,raw_content:'请自动识别超时订单并提醒仓储跟进',analyze_with_ai:true}})).json()).data
 await expect.poll(async()=> (await (await page.request.get(`${base}/requirements/${requirement.id}`)).json()).data.analysis_status).toBe('ANALYZED')
 await page.goto(`/coo?project_id=${project.id}`)
 await page.getByPlaceholder('告诉 Coo 你希望完成的工作…').fill('调查模拟订单履约异常，查询规范并建议跟进任务')
 await page.getByRole('button',{name:'发送目标'}).click()
 await expect(page.getByText('任务：跟进模拟订单未发货',{exact:true})).toBeVisible({timeout:15000})
 const before=(await (await page.request.get(`${base}/projects/${project.id}/tasks`)).json()).data.total
 expect(before).toBe(0)
 await page.screenshot({path:'test-results/coo-v4-confirmation.png',fullPage:true})
 await page.getByRole('button',{name:'确认执行',exact:true}).click()
 await expect(page.getByText('创建任务 · 已执行',{exact:true})).toBeVisible()
 const task=(await (await page.request.get(`${base}/projects/${project.id}/tasks`)).json()).data.items[0]
 await page.goto(`/projects/${project.id}/tasks/board?task_id=${task.id}`)
 await expect(page.getByRole('heading',{name:'任务留言',exact:true})).toBeVisible()
 await page.getByPlaceholder('留言或回复，协同跟进任务').fill('已联系仓库，请核实库存')
 await page.getByRole('button',{name:'发送留言',exact:true}).click();await expect(page.getByText('已联系仓库，请核实库存',{exact:true})).toBeVisible()
 await page.getByRole('button',{name:'回复',exact:true}).click()
 await page.getByPlaceholder('留言或回复，协同跟进任务').fill('仓库正在核查')
 await page.getByRole('button',{name:'发送留言',exact:true}).click();await expect(page.getByText('仓库正在核查',{exact:true})).toBeVisible()
 await page.goto(`/coo?project_id=${project.id}`)
 await page.getByPlaceholder('告诉 Coo 你希望完成的工作…').fill('请查询当前任务并留言跟进')
 await page.getByText('本轮允许 Coo 在当前授权范围内自动留言',{exact:true}).click()
 await page.getByRole('button',{name:'发送目标'}).click()
 await expect(page.getByText('Coo 留言 · 已执行',{exact:true})).toBeVisible({timeout:15000})
 const comments=(await (await page.request.get(`${base}/projects/${project.id}/tasks/${task.id}/comments`)).json()).data
 expect(comments.some((v:{actor_type:string})=>v.actor_type==='COO')).toBe(true)
 // Background worker sees the durable event without any browser polling requirement.
 const event=(await (await page.request.post(base+'/coo/events/simulated-order',{headers,data:{project_id:project.id,order_id:`ERP-${suffix}`}})).json()).data
 await expect.poll(async()=>{const list=(await (await page.request.get(base+'/coo/events')).json()).data;return list.find((v:{id:string})=>v.id===event.id)?.status},{timeout:25000}).toBe('SUCCEEDED')
 await page.goto('/coo/events');await expect(page.getByRole('heading',{name:'Coo 主动工作',exact:true})).toBeVisible()
 await expect(page.locator('.events-page .el-table').first().getByText('履约异常',{exact:false})).toBeVisible()
 await page.screenshot({path:'test-results/coo-v4-events.png',fullPage:true})
})
