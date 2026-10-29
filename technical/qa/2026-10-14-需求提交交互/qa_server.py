import asyncio
import os
import sys
from pathlib import Path

ROOT = Path('/Users/zhanggengyu/Documents/极简AI团队需求管理智能体')
QA_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.update({
    'DATABASE_URL': f'sqlite:///{QA_DIR}/test.db',
    'SHARED_PASSWORD': 'qa-20261014-password',
    'AUTH_HMAC_KEY': 'qa-hmac-key-20261014-isolated-only-32',
    'INVITATION_ENCRYPTION_KEY': 'qa-encryption-key-20261014-isolated-32',
    'SESSION_COOKIE_NAME': 'qa_requirement_session',
    'SESSION_COOKIE_SECURE': 'false',
    'DIFY_BASE_URL': 'http://127.0.0.1:8002/v1',
    'DIFY_API_KEY': 'qa-placeholder',
    'DIFY_TIMEOUT_SECONDS': '2',
})

if sys.argv[1] == 'setup':
    from alembic import command
    from alembic.config import Config
    from app.db.seed import main as seed
    from app.db.session import SessionLocal
    from app.services.auth_service import AuthService
    os.chdir(ROOT / 'backend')
    command.upgrade(Config('alembic.ini'), 'head')
    seed()
    with SessionLocal() as db:
        AuthService(db).bootstrap_admin(department_name='产品部', user_name='交互测试管理员')
    print('独立测试库与管理员准备完成')
elif sys.argv[1] == 'backend':
    import uvicorn
    from fastapi.middleware.cors import CORSMiddleware
    from app.main import app
    app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3001'],
                       allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
    uvicorn.run(app, host='127.0.0.1', port=8001)
elif sys.argv[1] == 'dify':
    import uvicorn
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    app = FastAPI()

    @app.post('/v1/workflows/run')
    async def run(request: Request):
        body = await request.json()
        content = body['inputs']['raw_content']
        if '连接失败' in content:
            return JSONResponse({'error': 'QA HTTP failure'}, status_code=503)
        if '超时' in content:
            await asyncio.sleep(4)
        if '慢速' in content:
            await asyncio.sleep(1)
        if '非法结果' in content:
            outputs = {'standard_content': '缺少必填分析字段'}
        else:
            outputs = {
                'standard_content': content,
                'business_goal': '验证需求提交、保存和前端反馈',
                'type': 'NEW_FEATURE', 'priority': 'P2',
                'is_fake': False, 'fake_reason': '有明确验证场景',
                'is_duplicate': False, 'related_id': '',
                'reference_rule': 'QA确定性模拟结果',
                'analysis_summary': '独立交互测试使用的模拟分析结果',
            }
        return {'workflow_run_id': 'qa-mock-run', 'data': {'status': 'succeeded', 'outputs': outputs}}

    uvicorn.run(app, host='127.0.0.1', port=8002)
