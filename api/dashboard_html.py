"""
Builds the dashboard page by stitching together dashboard_css.py and
dashboard_js.py.

The skeleton below is a plain triple-quoted string, NOT an f-string, and the
placeholders (__DASHBOARD_CSS__ / __DASHBOARD_JS__) are swapped in with
str.replace() rather than str.format(). Both choices matter for the same
reason: the CSS and JS text is full of literal `{`, `}`, and `${...}`
sequences, and both f-strings and .format() would try to parse those as
Python/format-spec expressions and blow up (this is exactly what caused the
88 Pylance errors on the old single-file version).
"""

from api.dashboard_css import DASHBOARD_CSS
from api.dashboard_js import DASHBOARD_JS

_DASHBOARD_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI News Wire -- Automation Console</title>
<style>
__DASHBOARD_CSS__
</style>
</head>
<body>
<div class="wrap">

  <header>
    <div class="brand">
      <div class="brand-mark">AI</div>
      <div>
        <h1>News Wire Automation</h1>
        <p>fetch &rarr; summarize &rarr; publish &rarr; log</p>
      </div>
    </div>
    <div class="status-pill"><span class="dot"></span>PIPELINE READY</div>
  </header>

  <div class="feed-controls">
    <div class="search-box">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
      <input type="text" id="searchInput" placeholder="Search headlines & summaries...">
    </div>
    <button class="refresh-btn" id="refreshBtn" title="Refresh feed">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/></svg>
    </button>
  </div>
  <div class="topic-pills" id="topicPills">
    <button class="pill active" data-topic="__all__">All</button>
  </div>
  <div id="feedList" class="feed-list"></div>
  <div id="feedEmpty" class="feed-empty" style="display:none;"></div>

  <div class="section-label">Agent Pipeline</div>
  <div class="agents" id="agents">
    <div class="agent-card">
      <div class="agent-idx">01 / NEWS FETCHER</div>
      <div class="agent-role">Headline scanner</div>
      <div class="agent-tool">tool: news_fetcher (SerperDev)</div>
    </div>
    <div class="agent-card">
      <div class="agent-idx">02 / SUMMARIZER</div>
      <div class="agent-role">Beat reporter</div>
      <div class="agent-tool">tool: summarize_article (Groq)</div>
    </div>
    <div class="agent-card">
      <div class="agent-idx">03 / PUBLISHER</div>
      <div class="agent-role">Slack gatekeeper</div>
      <div class="agent-tool">tool: post_to_slack</div>
    </div>
    <div class="agent-card">
      <div class="agent-idx">04 / LOGGER</div>
      <div class="agent-role">Paper trail</div>
      <div class="agent-tool">tool: log_to_sheet</div>
    </div>
  </div>

  <div class="trigger-panel">
    <div class="section-label" style="margin-bottom:0;">Manual Trigger</div>
    <div class="trigger-row">
      <input type="text" id="topicInput" class="key-input" placeholder="Enter a topic -- e.g. SpaceX, Bitcoin ETF (leave blank for default topics)" autocomplete="off" maxlength="150">
      <button id="runBtn" class="run-btn">Get News</button>
    </div>
    <div class="hint">
      Runs the live pipeline for whatever you type -- no key needed. Leave it blank to use the
      default topics instead. Protected by a short server-side cooldown (checked against the
      last logged story) so repeated clicks can't burn through API quota.
    </div>
    <div id="terminalLog" class="terminal-log"></div>
  </div>

  <div class="timeline">
    <div class="section-label" style="margin-bottom:0;">Run Sequence</div>
    <div class="tl-row">
      <div class="tl-step">
        <div class="tl-num">1</div>
        <div class="tl-title">Fetch</div>
        <div class="tl-desc">Pull fresh headlines per configured topic via SerperDev News API.</div>
      </div>
      <div class="tl-step">
        <div class="tl-num">2</div>
        <div class="tl-title">Summarize</div>
        <div class="tl-desc">Groq LLM compresses each article into a neutral 2&ndash;3 sentence update.</div>
      </div>
      <div class="tl-step">
        <div class="tl-num">3</div>
        <div class="tl-title">Publish</div>
        <div class="tl-desc">Every summary posts to the configured Slack channel via webhook.</div>
      </div>
      <div class="tl-step">
        <div class="tl-num">4</div>
        <div class="tl-title">Log</div>
        <div class="tl-desc">Every published story is appended as a row in Google Sheets.</div>
      </div>
    </div>
  </div>

  <div class="section-label">Schedule</div>
  <div class="schedule-panel">
    <div class="sched-card">
      <h3>Primary trigger</h3>
      <div class="big">Every 6h</div>
      <div class="sub">GitHub Actions cron (free, unrestricted schedule) calls this endpoint round the clock.</div>
    </div>
    <div class="sched-card">
      <h3>Fallback trigger</h3>
      <div class="big">Daily</div>
      <div class="sub">Vercel's own Hobby-plan cron (max 1x/day) hits the same endpoint as a safety net.</div>
    </div>
    <div class="sched-card">
      <h3>Next 6h boundary</h3>
      <div class="big" id="nextRun">--:--</div>
      <div class="sub" id="nextRunSub">UTC, computed locally</div>
    </div>
  </div>

  <footer>ai-news-automation-bot &middot; deployed on vercel &middot; no build step</footer>
</div>

<script>
__DASHBOARD_JS__
</script>
</body>
</html>
"""


def get_dashboard_html() -> str:
    """Assemble the full dashboard page. str.replace(), not .format() --
    see module docstring for why."""
    html = _DASHBOARD_HTML_TEMPLATE.replace("__DASHBOARD_CSS__", DASHBOARD_CSS)
    html = html.replace("__DASHBOARD_JS__", DASHBOARD_JS)
    return html