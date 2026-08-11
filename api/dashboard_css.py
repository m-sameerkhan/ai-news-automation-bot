"""
Plain triple-quoted string -- deliberately NOT an f-string. If this were an
f-string, every literal `{` and `}` in the CSS below (there are hundreds --
:root{...}, header{...}, etc.) would be parsed by Python as the start of an
interpolated expression, which is exactly what was breaking dashboard_html.py
before this split.
"""

DASHBOARD_CSS = """
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;500;600;700&display=swap');

:root{
  --bg:#0b0d0f;
  --panel:#131619;
  --panel-2:#181c1f;
  --border:#262b2f;
  --text:#e8e6e1;
  --muted:#8b9096;
  --amber:#f2a93c;
  --amber-dim:#8a6a2e;
  --green:#5ec98f;
  --red:#e0685f;
  --mono:'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
  --sans:'Inter', system-ui, -apple-system, sans-serif;
}
*{box-sizing:border-box; margin:0; padding:0;}
body{
  background:
    repeating-linear-gradient(0deg, rgba(255,255,255,0.015) 0px, rgba(255,255,255,0.015) 1px, transparent 1px, transparent 24px),
    var(--bg);
  color:var(--text);
  font-family:var(--sans);
  min-height:100vh;
  padding:32px 20px 60px;
}
.wrap{max-width:980px; margin:0 auto;}

/* Header */
header{
  display:flex; align-items:center; justify-content:space-between;
  flex-wrap:wrap; gap:16px;
  padding-bottom:22px; margin-bottom:28px;
  border-bottom:1px solid var(--border);
}
.brand{display:flex; align-items:center; gap:14px;}
.brand-mark{
  width:42px; height:42px; border-radius:8px;
  background:linear-gradient(145deg, var(--amber), #c97f1f);
  display:flex; align-items:center; justify-content:center;
  font-family:var(--mono); font-weight:700; color:#0b0d0f; font-size:15px;
}
.brand h1{font-size:19px; font-weight:700; letter-spacing:-0.01em;}
.brand p{font-size:12.5px; color:var(--muted); font-family:var(--mono); margin-top:2px;}
.status-pill{
  display:flex; align-items:center; gap:8px;
  background:var(--panel); border:1px solid var(--border);
  padding:8px 14px; border-radius:100px;
  font-family:var(--mono); font-size:12px; color:var(--green);
}
.dot{width:7px; height:7px; border-radius:50%; background:var(--green); animation:pulse 2s infinite;}
@keyframes pulse{0%,100%{opacity:1;} 50%{opacity:.35;}}

/* Pipeline strip */
.section-label{
  font-family:var(--mono); font-size:11.5px; color:var(--muted);
  text-transform:uppercase; letter-spacing:.08em; margin-bottom:12px;
}
.agents{
  display:grid; grid-template-columns:repeat(auto-fit, minmax(200px,1fr));
  gap:12px; margin-bottom:32px;
}
.agent-card{
  background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:16px; position:relative; overflow:hidden;
}
.agent-card::before{
  content:""; position:absolute; top:0; left:0; width:100%; height:2px;
  background:var(--amber-dim);
}
.agent-idx{font-family:var(--mono); font-size:11px; color:var(--amber); margin-bottom:8px;}
.agent-role{font-weight:600; font-size:14.5px; margin-bottom:4px;}
.agent-tool{font-family:var(--mono); font-size:11.5px; color:var(--muted);}

/* Trigger panel */
.trigger-panel{
  background:var(--panel); border:1px solid var(--border); border-radius:12px;
  padding:24px; margin-bottom:24px;
}
.trigger-row{display:flex; gap:10px; flex-wrap:wrap; margin-top:16px;}
.key-input{
  flex:1; min-width:200px;
  background:var(--panel-2); border:1px solid var(--border); color:var(--text);
  padding:11px 14px; border-radius:8px; font-family:var(--mono); font-size:13px;
}
.key-input:focus{outline:none; border-color:var(--amber-dim);}
.run-btn{
  background:var(--amber); color:#191204; border:none;
  padding:11px 22px; border-radius:8px; font-weight:700; font-size:13.5px;
  cursor:pointer; font-family:var(--sans); white-space:nowrap;
  transition:filter .15s;
}
.run-btn:hover{filter:brightness(1.08);}
.run-btn:disabled{opacity:.5; cursor:not-allowed;}
.hint{font-size:12px; color:var(--muted); margin-top:10px; line-height:1.5;}

.terminal-log{
  margin-top:16px; background:#0a0c0d; border:1px solid var(--border);
  border-radius:8px; padding:16px 18px; font-family:var(--mono); font-size:13px;
  display:none;
}
.terminal-log.ok{border-color:rgba(94,201,143,.35);}
.terminal-log.err{border-color:rgba(224,104,95,.35);}
.log-line{
  color:#c7ccd1; line-height:1.9; opacity:0; transform:translateY(4px);
  animation:logIn .25s ease forwards;
}
.log-line::before{content:"> "; color:var(--muted);}
.log-line.success{color:var(--green);}
.log-line.error{color:var(--red);}
.log-line.warn{color:var(--amber);}
@keyframes logIn{to{opacity:1; transform:translateY(0);}}

/* Timeline */
.timeline{
  background:var(--panel); border:1px solid var(--border); border-radius:12px;
  padding:24px; margin-bottom:24px;
}
.tl-row{display:flex; align-items:flex-start; gap:0; overflow-x:auto; padding-top:8px;}
.tl-step{flex:1; min-width:150px; position:relative; padding-right:14px;}
.tl-num{
  width:26px; height:26px; border-radius:50%;
  background:var(--panel-2); border:1px solid var(--amber-dim);
  color:var(--amber); font-family:var(--mono); font-size:12px; font-weight:700;
  display:flex; align-items:center; justify-content:center; margin-bottom:10px;
}
.tl-step:not(:last-child)::after{
  content:""; position:absolute; top:13px; left:38px; right:0; height:1px;
  background:var(--border);
}
.tl-title{font-weight:600; font-size:13.5px; margin-bottom:4px;}
.tl-desc{font-size:12px; color:var(--muted); line-height:1.5;}

/* Footer / schedule */
.schedule-panel{
  display:grid; grid-template-columns:repeat(auto-fit, minmax(220px,1fr));
  gap:12px;
}
.sched-card{
  background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:16px;
}
.sched-card h3{font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; font-weight:600; margin-bottom:8px;}
.sched-card .big{font-family:var(--mono); font-size:20px; color:var(--amber); font-weight:700;}
.sched-card .sub{font-size:12px; color:var(--muted); margin-top:4px;}

footer{text-align:center; margin-top:36px; font-size:11.5px; color:var(--muted); font-family:var(--mono);}

/* Feed */
.feed-controls{
  display:flex; gap:10px; align-items:center; margin-bottom:14px; flex-wrap:wrap;
}
.search-box{
  flex:1; min-width:220px; display:flex; align-items:center; gap:8px;
  background:var(--panel); border:1px solid var(--border); border-radius:8px;
  padding:10px 14px;
}
.search-box svg{flex-shrink:0; opacity:.5;}
.search-box input{
  flex:1; background:none; border:none; color:var(--text);
  font-family:var(--sans); font-size:13.5px;
}
.search-box input:focus{outline:none;}
.refresh-btn{
  background:var(--panel); border:1px solid var(--border); color:var(--muted);
  width:39px; height:39px; border-radius:8px; cursor:pointer;
  display:flex; align-items:center; justify-content:center; transition:.15s;
}
.refresh-btn:hover{color:var(--amber); border-color:var(--amber-dim);}
.refresh-btn.spinning svg{animation:spin .7s linear infinite;}
@keyframes spin{from{transform:rotate(0);} to{transform:rotate(360deg);}}
.topic-pills{display:flex; gap:8px; margin-bottom:20px; flex-wrap:wrap;}
.pill{
  background:var(--panel); border:1px solid var(--border); color:var(--muted);
  padding:7px 15px; border-radius:100px; font-size:12.5px; font-weight:600;
  cursor:pointer; font-family:var(--sans); transition:.15s;
}
.pill.active{background:var(--amber); color:#191204; border-color:var(--amber);}
.pill:not(.active):hover{border-color:var(--amber-dim); color:var(--text);}

.feed-list{display:flex; flex-direction:column; gap:12px; margin-bottom:36px;}
.story-card{
  background:var(--panel); border:1px solid var(--border); border-radius:10px;
  padding:18px 20px;
}
.story-top{display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; gap:10px;}
.topic-badge{
  background:rgba(242,169,60,.12); color:var(--amber);
  font-family:var(--mono); font-size:10.5px; font-weight:700;
  padding:3px 9px; border-radius:5px; text-transform:uppercase; letter-spacing:.04em;
}
.story-time{font-family:var(--mono); font-size:11.5px; color:var(--muted); white-space:nowrap;}
.story-headline{font-size:16px; font-weight:700; margin-bottom:8px; line-height:1.35;}
.story-summary{font-size:13.5px; color:var(--muted); line-height:1.6; margin-bottom:12px;}
.story-sources{display:flex; gap:14px; flex-wrap:wrap;}
.story-sources a{color:var(--amber); font-size:12.5px; text-decoration:none; font-weight:600;}
.story-sources a:hover{text-decoration:underline;}
.feed-empty{
  text-align:center; padding:40px 20px; color:var(--muted); font-size:13.5px;
  background:var(--panel); border:1px dashed var(--border); border-radius:10px; margin-bottom:36px;
  line-height:1.6;
}
"""