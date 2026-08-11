"""
Plain triple-quoted string -- deliberately NOT an f-string. The JS below is
full of `${...}` template literals and `{ ... }` blocks; as an f-string every
one of those would be treated as a Python interpolation and fail to parse.
"""

DASHBOARD_JS = """
// Purely client-side countdown to the next 00/06/12/18 UTC boundary.
// This is real arithmetic against the current clock, not fabricated status.
function updateNextRun(){
  const now = new Date();
  const boundaries = [0,6,12,18];
  const utcHour = now.getUTCHours();
  let nextHour = boundaries.find(h => h > utcHour);
  let target = new Date(now);
  if (nextHour === undefined) {
    target.setUTCDate(target.getUTCDate() + 1);
    nextHour = 0;
  }
  target.setUTCHours(nextHour, 0, 0, 0);
  const diffMs = target - now;
  const h = Math.floor(diffMs / 3600000);
  const m = Math.floor((diffMs % 3600000) / 60000);
  document.getElementById('nextRun').textContent = `${h}h ${m}m`;
  document.getElementById('nextRunSub').textContent = `~${String(nextHour).padStart(2,'0')}:00 UTC`;
}
updateNextRun();
setInterval(updateNextRun, 30000);

// --- News feed: fetches whatever the Logger agent already wrote to the
// Sheet, then filters/searches entirely client-side (no re-fetch per
// keystroke or pill click). ---
let allStories = [];
let activeTopic = '__all__';

function timeAgo(isoString){
  const then = new Date(isoString);
  if (isNaN(then)) return '';
  const diffSec = Math.floor((Date.now() - then.getTime()) / 1000);
  if (diffSec < 60) return 'just now';
  if (diffSec < 3600) return Math.floor(diffSec/60) + 'm ago';
  if (diffSec < 86400) return Math.floor(diffSec/3600) + 'h ago';
  return Math.floor(diffSec/86400) + 'd ago';
}

function escapeHtml(str){
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function renderPills(){
  const topics = [...new Set(allStories.map(s => s.topic).filter(Boolean))];
  const container = document.getElementById('topicPills');
  container.innerHTML = '';
  const makePill = (label, value) => {
    const btn = document.createElement('button');
    btn.className = 'pill' + (activeTopic === value ? ' active' : '');
    btn.textContent = label;
    btn.dataset.topic = value;
    btn.addEventListener('click', () => { activeTopic = value; renderPills(); renderFeed(); });
    return btn;
  };
  container.appendChild(makePill('All', '__all__'));
  topics.forEach(t => container.appendChild(makePill(t, t)));
}

function renderFeed(){
  const q = (document.getElementById('searchInput').value || '').toLowerCase().trim();
  const listEl = document.getElementById('feedList');
  const emptyEl = document.getElementById('feedEmpty');

  let items = allStories;
  if (activeTopic !== '__all__') items = items.filter(s => s.topic === activeTopic);
  if (q) items = items.filter(s =>
    (s.headline || '').toLowerCase().includes(q) ||
    (s.summary || '').toLowerCase().includes(q)
  );

  if (items.length === 0) {
    listEl.innerHTML = '';
    emptyEl.style.display = 'block';
    emptyEl.textContent = allStories.length === 0
      ? 'No stories logged yet -- run the pipeline once (below) and they will appear here.'
      : 'No stories match your search/filter.';
    return;
  }
  emptyEl.style.display = 'none';

  listEl.innerHTML = items.map(s => `
    <div class="story-card">
      <div class="story-top">
        <span class="topic-badge">${escapeHtml(s.topic || 'news')}</span>
        <span class="story-time">${timeAgo(s.date)}</span>
      </div>
      <div class="story-headline">${escapeHtml(s.headline)}</div>
      <div class="story-summary">${escapeHtml(s.summary)}</div>
      <div class="story-sources">
        ${(s.source_urls || []).map((u, i) => `<a href="${escapeHtml(u)}" target="_blank" rel="noopener">Source ${i+1} &nearr;</a>`).join('')}
      </div>
    </div>
  `).join('');
}

async function loadFeed(){
  const btn = document.getElementById('refreshBtn');
  btn.classList.add('spinning');
  try {
    const res = await fetch(window.location.pathname + '?feed=json');
    const data = await res.json();
    allStories = data.items || [];
    renderPills();
    renderFeed();
  } catch (err) {
    document.getElementById('feedEmpty').style.display = 'block';
    document.getElementById('feedEmpty').textContent = 'Could not load the feed: ' + err.message;
  } finally {
    btn.classList.remove('spinning');
  }
}

document.getElementById('searchInput').addEventListener('input', renderFeed);
document.getElementById('refreshBtn').addEventListener('click', loadFeed);
loadFeed();

// Manual trigger -- type any topic, no secret needed, cooldown-protected server-side.
const runBtn = document.getElementById('runBtn');
const topicInput = document.getElementById('topicInput');
const terminalLog = document.getElementById('terminalLog');

function appendLogLine(text, cls, delayMs){
  setTimeout(() => {
    const line = document.createElement('div');
    line.className = 'log-line' + (cls ? ' ' + cls : '');
    line.textContent = text;
    terminalLog.appendChild(line);
    terminalLog.scrollTop = terminalLog.scrollHeight;
  }, delayMs);
}

function playRunLog(status, data, topicLabel){
  terminalLog.innerHTML = '';
  terminalLog.style.display = 'block';

  if (status === 429) {
    terminalLog.className = 'terminal-log';
    appendLogLine((data.error || 'Pipeline on cooldown -- try again shortly.'), 'warn', 0);
  } else if (status === 200) {
    const used = (data.topics && data.topics.length) ? data.topics.join(', ') : topicLabel;
    const count = data.logged_count;
    appendLogLine(`Fetching news for: ${used}...`, '', 0);

    if (count === null || count === undefined) {
      // Couldn't verify against the Sheet -- say so honestly instead of
      // claiming success we didn't check.
      terminalLog.className = 'terminal-log';
      appendLogLine('Pipeline finished running.', 'success', 500);
      appendLogLine('Could not verify what was logged -- check the Sheet directly.', 'warn', 1000);
    } else if (count > 0) {
      terminalLog.className = 'terminal-log ok';
      appendLogLine(`Pipeline completed -- ${count} ${count === 1 ? 'story' : 'stories'} logged!`, 'success', 500);
      appendLogLine('Posted to Slack & logged to Google Sheets.', '', 1000);
      appendLogLine('Refreshing feed with the new stories...', '', 1500);
      setTimeout(loadFeed, 1900);
    } else {
      // Pipeline ran fine but found/logged nothing for this topic --
      // this is the honest outcome, not a hardcoded success message.
      terminalLog.className = 'terminal-log';
      appendLogLine(`No headlines found for "${used}" -- nothing was posted or logged.`, 'warn', 500);
      appendLogLine('Try a broader or differently-worded topic.', '', 1000);
    }
  } else {
    terminalLog.className = 'terminal-log err';
    const errMsg = (data && (data.error || data.note)) || 'Unknown error';
    appendLogLine('Pipeline failed: ' + errMsg, 'error', 0);
  }
}

runBtn.addEventListener('click', async () => {
  const topic = topicInput.value.trim();
  const topicLabel = topic || 'default topics';

  runBtn.disabled = true;
  runBtn.textContent = 'Running...';
  terminalLog.style.display = 'block';
  terminalLog.className = 'terminal-log';
  terminalLog.innerHTML = '';
  appendLogLine(`Fetching news for: ${topicLabel}...`, '', 0);

  try {
    const res = await fetch(window.location.pathname, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic })
    });
    const data = await res.json();
    playRunLog(res.status, data, topicLabel);
  } catch (err) {
    terminalLog.className = 'terminal-log err';
    appendLogLine('Request failed: ' + err.message, 'error', 400);
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = 'Get News';
  }
});
"""