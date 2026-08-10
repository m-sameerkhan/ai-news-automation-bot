"""
Vercel serverless entrypoint. Wraps the existing CrewAI pipeline (crew.py)
behind an HTTP endpoint so it can be deployed on Vercel and triggered by an
external scheduler (this repo's GitHub Actions cron calls it every 6 hours,
since Vercel Hobby cron only supports once-per-day).

Deployed path: /api/run-pipeline

Auth: requires header  Authorization: Bearer <RUN_SECRET>
where RUN_SECRET is a Vercel project env var you set yourself (separate from
Vercel's own CRON_SECRET, since we're triggering from GitHub Actions, not
Vercel's built-in cron).
"""
import os
import sys
import json
import traceback
from http.server import BaseHTTPRequestHandler

# CrewAI's chromadb submodule creates a default storage directory at IMPORT
# TIME (not when memory/RAG is actually used) -- it assumes it can write to
# the user's home directory. Vercel's serverless filesystem is read-only
# except /tmp, so this MUST be set before `from crew import run_news_crew`
# runs below, or the import itself crashes with a read-only filesystem error.
os.environ.setdefault("CREWAI_STORAGE_DIR", "/tmp/crewai_storage")

# api/ is one level below the project root where crew.py, agents.py,
# tasks.py, config.py and tools/ live -- add the root to sys.path so the
# existing absolute imports in those files keep working unmodified.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class handler(BaseHTTPRequestHandler):
    def _unauthorized(self):
        self.send_response(401)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "unauthorized"}).encode())

    def _check_auth(self) -> bool:
        expected = os.environ.get("RUN_SECRET", "")
        if not expected:
            # Fail closed: if you forget to set RUN_SECRET in Vercel, the
            # endpoint refuses to run rather than being left wide open.
            return False
        got = self.headers.get("Authorization", "")
        return got == f"Bearer {expected}"

    def _run(self):
        if not self._check_auth():
            self._unauthorized()
            return

        try:
            from crew import run_news_crew
            result = run_news_crew()
            body = {"status": "ok", "result": str(result)}
            code = 200
        except Exception as exc:  # noqa: BLE001
            body = {
                "status": "error",
                "error": str(exc),
                "trace": traceback.format_exc(),
            }
            code = 500

        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_GET(self):
        self._run()

    def do_POST(self):
        self._run()