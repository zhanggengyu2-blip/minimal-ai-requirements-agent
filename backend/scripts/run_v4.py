"""Start the existing API and durable Coo event worker with one command."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))
from app.db.migrations import upgrade_database
from app.db.seed import seed_default_departments

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8000);args=parser.parse_args()
    upgrade_database();seed_default_departments()
    children=[]
    def stop(*_):
        for child in children:
            if child.poll() is None:child.terminate()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        children.append(subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(args.port)]))
        children.append(subprocess.Popen([sys.executable,'-m','app.coo.worker']))
        while all(child.poll() is None for child in children):time.sleep(.5)
    finally:
        stop()
        for child in children:
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:child.kill();child.wait()
    if any(child.returncode not in (0,-signal.SIGTERM) for child in children):return 1
    return 0

if __name__=='__main__':sys.exit(main())
