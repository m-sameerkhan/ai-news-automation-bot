"""
Quick local test server -- runs the same `handler` class from
api/run-pipeline.py directly on Python's stdlib HTTPServer.

This is NOT a substitute for `vercel dev` (it won't apply vercel.json
routing, and Vercel's automatic CRON_SECRET header won't be sent), but it's
the fastest way to sanity-check the dashboard and pipeline endpoint without
installing the Vercel CLI.

Usage:
    python local_dev_server.py
    -> serves on http://localhost:8000
"""
import os
import sys
from http.server import HTTPServer

# Load .env manually since vercel dev normally does this for you.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("(python-dotenv not installed -- reading only real env vars. "
          "`pip install python-dotenv` if you want .env support here.)")

sys.path.insert(0, os.path.dirname(__file__))

# run-pipeline.py has a hyphen, so it isn't a normal importable module name --
# import it via importlib instead of `from api.run-pipeline import handler`.
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "run_pipeline", os.path.join(os.path.dirname(__file__), "api", "run-pipeline.py")
)
_run_pipeline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_run_pipeline)

if __name__ == "__main__":
    port = 8000
    server = HTTPServer(("localhost", port), _run_pipeline.handler)
    print(f"Serving dashboard at http://localhost:{port}")
    print(f"Feed:       http://localhost:{port}/?feed=json")
    print(f"Manual run: curl -X POST http://localhost:{port}")
    print("            (no auth needed -- gated by the server-side cooldown "
          "instead; run it twice quickly to see a 429)")
    print(f"Cron/format=json path (still secret-gated): "
          f"curl http://localhost:{port}/?format=json "
          f"-H \"Authorization: Bearer $RUN_SECRET\"")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")