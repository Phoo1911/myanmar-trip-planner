"""One free web instance; only Next.js is publicly bound."""
import os, signal, subprocess, sys, time
from pathlib import Path
root=Path(__file__).resolve().parent
subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=root/'backend',check=True)
children=[]
def stop(signum=None,frame=None):
    for child in children:
        if child.poll() is None:child.terminate()
    for child in children:
        try:child.wait(timeout=8)
        except subprocess.TimeoutExpired:child.kill();child.wait()
    if signum is not None:raise SystemExit(0)
signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)
try:
    children.append(subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000','--workers','1'],cwd=root/'backend'))
    children.append(subprocess.Popen(['node','server.js'],cwd=root/'web',env={**os.environ,'HOSTNAME':'0.0.0.0'}))
    while all(child.poll() is None for child in children):time.sleep(1)
    raise SystemExit(1)
finally:stop()
