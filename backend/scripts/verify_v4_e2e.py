"""Run both browser flows with an isolated SQLite database and a controlled model HTTP fixture."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[2]

def main():
    if not shutil.which('pnpm'):
        raise SystemExit('请先安装 Node.js / pnpm，并确保它们在 PATH 中。')
    for port in (8000,3000,8416):
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',port))==0:
                raise SystemExit(f'端口 {port} 正在使用。为避免测试误连已有业务系统，请先自行停止该服务。')
    folder=Path(tempfile.mkdtemp(prefix='coo-v4-e2e-'))
    env=os.environ.copy()
    env.update(DATABASE_URL=f'sqlite:///{folder / "test.db"}',APP_ENV='test',DEBUG='false',
        SHARED_PASSWORD='e2e-shared-password',AUTH_HMAC_KEY='e2e-auth-key-012345678901234567890123',
        INVITATION_ENCRYPTION_KEY='e2e-invite-key-012345678901234567890',
        E2E_COO_FIXTURE='1',E2E_SHARED_PASSWORD='e2e-shared-password',E2E_ADMIN_DEPARTMENT='产品部',E2E_ADMIN_NAME='E2E管理员',
        COO_BASE_URL='http://127.0.0.1:8416/v1',COO_API_KEY='controlled-test-fixture',COO_MODEL='controlled-fixture-NOT-REAL-LLM',
        KNOWLEDGE_EMBEDDING_BASE_URL='http://127.0.0.1:8416/v1',KNOWLEDGE_EMBEDDING_API_KEY='controlled-test-fixture',KNOWLEDGE_EMBEDDING_MODEL='controlled-embedding',
        KNOWLEDGE_RERANK_BASE_URL='http://127.0.0.1:8416/v1',KNOWLEDGE_RERANK_API_KEY='controlled-test-fixture',KNOWLEDGE_RERANK_MODEL='controlled-rerank',KNOWLEDGE_RERANK_FORMAT='standard')
    env['NO_PROXY']='127.0.0.1,localhost'
    children=[];logs=[]
    local_http=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def wait_ready(url):
        for _ in range(100):
            if any(child.poll() is not None for child in children):raise RuntimeError('测试服务启动失败，请查看临时目录日志')
            try:
                with local_http.open(url,timeout=1):return
            except Exception:time.sleep(.2)
        raise RuntimeError('测试服务启动超时')
    try:
        subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT/'backend',env=env,check=True)
        subprocess.run([sys.executable,'-m','app.db.seed'],cwd=ROOT/'backend',env=env,check=True)
        subprocess.run([sys.executable,'scripts/bootstrap_admin.py','--department','产品部','--name','E2E管理员'],cwd=ROOT/'backend',env=env,check=True)
        commands=[([sys.executable,'backend/tests/model_fixture_server.py'],ROOT),
                  ([sys.executable,'backend/scripts/run_v4.py'],ROOT),
                  (['pnpm','--dir','frontend','run','dev'],ROOT)]
        for i,(command,cwd) in enumerate(commands):
            log=(folder/f'service-{i}.log').open('w');logs.append(log)
            children.append(subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT))
        wait_ready('http://127.0.0.1:8000/api/v1/ready');wait_ready('http://127.0.0.1:3000')
        print('运行受控模型浏览器验收。此服务不是真实 LLM。测试文件与日志：',folder)
        return subprocess.run(['pnpm','--dir','frontend','test:e2e'],cwd=ROOT,env=env).returncode
    finally:
        for child in children:
            if child.poll() is None:child.terminate()
        for child in children:
            try:child.wait(timeout=8)
            except subprocess.TimeoutExpired:child.kill();child.wait()
        for log in logs:log.close()
        print('测试使用独立数据库；临时记录：',folder)

if __name__=='__main__':sys.exit(main())
