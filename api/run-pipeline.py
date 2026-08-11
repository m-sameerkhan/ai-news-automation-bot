"""
Vercel serverless entrypoint. Wraps the existing CrewAI pipeline (crew.py)
behind one HTTP endpoint that does double duty:

  - Plain browser GET            -> serves the dashboard UI (dashboard_html.py)
  - GET  ?feed=json              -> read-only, NO auth, returns recently logged
                                     stories from the Sheet for the dashboard's
                                     news feed (nothing here executes the crew
                                     or costs API credits -- it's a read)
  - GET  ?format=json            -> runs the pipeline, requires auth, returns JSON
  - GET  from Vercel's own cron  -> runs the pipeline, requires auth, returns JSON
  - POST (dashboard "Get News")  -> runs the pipeline, NO secret required --
                                     gated instead by a server-side cooldown
                                     checked against the last logged story's
                                     timestamp, so repeat clicks can't burn
                                     through API quota. Returns 429 while on
                                     cooldown. Body is {"topic": "..."}, a
                                     comma-separated topic string (blank =
                                     use the default configured topics). The
                                     200 response includes "topics" (what was
                                     actually searched) and "logged_count"
                                     (how many new rows landed in the Sheet
                                     during this run, or null if that
                                     couldn't be verified).

Auth (GET paths only) accepts EITHER of two secrets, both compared as
`Authorization: Bearer <value>`:
  - RUN_SECRET   -> set by you, used by the GitHub Actions 6-hour cron.
  - CRON_SECRET  -> set by you, automatically sent by Vercel's own built-in
                    cron (Vercel adds this header itself when the env var
                    exists -- see vercel.json).

A plain page load never executes the pipeline. That matters: without this
gate, anyone (or a crawler) hitting the URL with an `Accept: application/json`
header would silently burn your Groq/Serper/Sheets quota.
"""
import os
import sys
import json
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# CrewAI's chromadb submodule creates a default storage directory at IMPORT
# TIME -- Vercel's filesystem is read-only except /tmp, so this MUST be set
# before `from crew import run_news_crew` runs, or the import itself crashes.
os.environ.setdefault("CREWAI_STORAGE_DIR", "/tmp/crewai_storage")

# api/ is one level below the project root where crew.py, agents.py, etc.
# live -- add both dirs to sys.path so imports keep working unmodified.
_HERE = os.path.dirname(__file__)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, ".."))

from api.dashboard_html import get_dashboard_html

# How long the manual "Run Pipeline Now" button stays disabled server-side
# after the last logged story. Override with RUN_COOLDOWN_SECONDS in env if
# you want it shorter/longer than the 5-minute default.
_DEFAULT_COOLDOWN_SECONDS = 300


def _expected_secrets() -> set:
    return {s for s in (os.environ.get("RUN_SECRET", ""), os.environ.get("CRON_SECRET", "")) if s}


def _is_authorized(headers) -> bool:
    expected = _expected_secrets()
    if not expected:
        # Fail closed: if neither secret is configured in Vercel, refuse to
        # run rather than being left wide open.
        return False
    got = headers.get("Authorization", "")
    return got in {f"Bearer {s}" for s in expected}


def _cooldown_seconds() -> int:
    try:
        return int(os.environ.get("RUN_COOLDOWN_SECONDS", _DEFAULT_COOLDOWN_SECONDS))
    except ValueError:
        return _DEFAULT_COOLDOWN_SECONDS


def _seconds_since_last_story():
    """Returns seconds since the most recently logged story's timestamp, or
    None if that can't be determined (no stories yet, Sheets not configured,
    unparseable date, etc.) -- in which case we don't block the run."""
    try:
        from tools.sheets_tool import read_recent_stories
        items = read_recent_stories(limit=1)
        if not items:
            return None
        raw_date = items[0].get("date")
        if not raw_date:
            return None
        last = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - last).total_seconds()
    except Exception:  # noqa: BLE001
        # Sheets not configured, network hiccup, bad date format, etc. --
        # don't let a broken cooldown check block a legitimate manual run.
        return None


def _count_new_stories_since(start_time) -> int | None:
    """How many rows the Logger agent actually wrote during this run, by
    comparing each recent row's timestamp against start_time. Returns None
    (not 0) if this can't be determined, so the caller can tell "verified
    zero" apart from "couldn't check" -- those are different things to tell
    the user."""
    try:
        from tools.sheets_tool import read_recent_stories
        items = read_recent_stories(limit=50)
        count = 0
        for item in items:
            raw_date = item.get("date")
            if not raw_date:
                continue
            dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt > start_time:
                count += 1
        return count
    except Exception:  # noqa: BLE001
        return None


class handler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, body: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, indent=2).encode("utf-8"))

    def _send_html(self, code: int, html: str):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _read_json_body(self) -> dict:
        """Best-effort JSON body parse. Returns {} for an empty/missing/
        malformed body rather than raising -- a bad body just means "no
        topic override", not a hard failure."""
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        if not length:
            return {}
        try:
            raw = self.rfile.read(length)
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:  # noqa: BLE001
            return {}

    def _execute_pipeline(self, topics=None) -> dict:
        from crew import run_news_crew
        result = run_news_crew(topics=topics)
        return {
            "status": "ok",
            "service": "AI News Automation Bot",
            "success": True,
            "result": str(result),
        }

    def _serve_feed(self):
        # Read-only: pulls whatever the Logger agent has already written to
        # the Sheet. No secret required -- it can't trigger a run or spend
        # any API credit, it only displays past results.
        try:
            from tools.sheets_tool import read_recent_stories
            items = read_recent_stories(limit=30)
            self._send_json(200, {"success": True, "configured": True, "items": items})
        except Exception as exc:  # noqa: BLE001
            # Most common case: GOOGLE_SHEET_ID / service account not set yet.
            # Still 200 so the dashboard can render a clean empty state
            # instead of an error toast.
            self._send_json(200, {
                "success": True,
                "configured": False,
                "items": [],
                "note": str(exc),
            })

    def _wants_dashboard(self, query: dict) -> bool:
        if query.get("format", [""])[0] == "json":
            return False
        if self.headers.get("x-vercel-cron") == "1":
            return False
        accept = self.headers.get("Accept", "")
        if "application/json" in accept and "text/html" not in accept:
            return False
        return True

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)

        if query.get("feed", [""])[0] == "json":
            self._serve_feed()
            return

        if self._wants_dashboard(query):
            self._send_html(200, get_dashboard_html())
            return

        # Only the cron/format=json path reaches here -- still secret-gated.
        if not _is_authorized(self.headers):
            self._send_json(401, {"success": False, "error": "unauthorized"})
            return

        try:
            self._send_json(200, self._execute_pipeline())
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {
                "success": False,
                "error": str(exc),
                "trace": traceback.format_exc(),
            })

    def do_POST(self):
        # Manual "Get News" trigger from the dashboard. No secret required --
        # gated by a cooldown against the last logged story instead, so a
        # public dashboard can't be used to spam the pipeline and burn
        # through API quota. Body is {"topic": "..."} -- a comma-separated
        # string of one or more topics, or blank/absent to use the default
        # configured topics (same as the cron runs).
        body = self._read_json_body()
        topic_raw = str(body.get("topic") or "").strip()
        topics = [t.strip() for t in topic_raw.split(",") if t.strip()] or None

        elapsed = _seconds_since_last_story()
        cooldown = _cooldown_seconds()
        if elapsed is not None and elapsed < cooldown:
            remaining = int(cooldown - elapsed)
            self._send_json(429, {
                "success": False,
                "error": f"Pipeline ran recently -- try again in {remaining}s.",
                "retry_after_seconds": remaining,
            })
            return

        start_time = datetime.now(timezone.utc)
        try:
            result = self._execute_pipeline(topics=topics)
            result["topics"] = topics
            result["logged_count"] = _count_new_stories_since(start_time)
            self._send_json(200, result)
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {
                "success": False,
                "error": str(exc),
                "trace": traceback.format_exc(),
            })