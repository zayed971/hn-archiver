"""
HN Market Intelligence Dashboard
Flask web dashboard for Hacker News front-page data.
"""

from flask import Flask, Response, jsonify, request
import csv, os, json, re, subprocess
from datetime import datetime
from collections import defaultdict, Counter

app = Flask(__name__)

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CSV_PATH    = os.path.join(BASE_DIR, 'hn_archive.csv')
SCRAPER_PATH = os.path.join(BASE_DIR, 'hn_scraper.py')

_cache = {}

CAT_COLORS = {
    'AI/ML':       '#00b4d8',
    'Programming': '#9d6ef8',
    'Big Tech':    '#3b82f6',
    'Security':    '#ef4444',
    'Startups':    '#f59e0b',
    'Other':       '#52525b',
}

# ── Data layer ────────────────────────────────────────────────────────────────

def parse_ts(ts):
    for fmt in ('%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime(ts.strip(), fmt)
        except ValueError:
            continue
    return None

def load_stories():
    if 'stories' in _cache:
        return _cache['stories']
    best = {}
    try:
        with open(CSV_PATH, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                try:
                    hn_id = (row.get('hn_id') or '').strip()
                    if not hn_id:
                        continue
                    row['points']   = int(row.get('points')   or 0)
                    row['comments'] = int(row.get('comments') or 0)
                    row['rank']     = int(row.get('rank')     or 0)
                    row['_dt']      = parse_ts(row.get('timestamp') or '')
                    if hn_id not in best or row['points'] > best[hn_id]['points']:
                        best[hn_id] = row
                except (ValueError, TypeError):
                    continue
    except FileNotFoundError:
        _cache['stories'] = []
        return []
    stories = sorted(best.values(), key=lambda x: x['points'], reverse=True)
    _cache['stories'] = stories
    return stories

def bust_cache():
    _cache.clear()

# ── Shared CSS ────────────────────────────────────────────────────────────────

CSS = """
:root {
    --bg:      #0c0c10;
    --surface: #13131a;
    --card:    #191921;
    --border:  #22222e;
    --text:    #e2e2ea;
    --muted:   #6a6a7a;
    --accent:  #00d4a8;
}
* { margin:0; padding:0; box-sizing:border-box; }
body {
    background:var(--bg); color:var(--text);
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    font-size:14px; line-height:1.5;
}
a { color:var(--accent); text-decoration:none; }
a:hover { text-decoration:underline; }

.nav {
    background:var(--surface); border-bottom:1px solid var(--border);
    padding:0 24px; display:flex; align-items:center; height:52px;
    gap:4px; position:sticky; top:0; z-index:100;
}
.nav-brand {
    font-size:15px; font-weight:700; color:var(--accent);
    letter-spacing:-.3px; margin-right:20px; text-decoration:none;
}
.nav-link {
    color:var(--muted); padding:6px 12px; border-radius:6px;
    font-size:13px; text-decoration:none; transition:color .15s,background .15s;
}
.nav-link:hover { color:var(--text); background:var(--card); }
.nav-link.active { color:var(--text); background:var(--card); }
.nav-spacer { flex:1; }
.nav-meta { font-size:12px; color:var(--muted); font-variant-numeric:tabular-nums; }

.page { max-width:1280px; margin:0 auto; padding:28px 24px 64px; }
.page-title { font-size:22px; font-weight:700; margin-bottom:4px; }
.page-sub { font-size:13px; color:var(--muted); margin-bottom:28px; }

.stats-row {
    display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
    gap:12px; margin-bottom:24px;
}
.stat-card {
    background:var(--card); border:1px solid var(--border);
    border-radius:10px; padding:16px 20px;
}
.stat-label {
    font-size:11px; text-transform:uppercase; letter-spacing:.06em;
    color:var(--muted); margin-bottom:6px;
}
.stat-value { font-size:26px; font-weight:700; font-variant-numeric:tabular-nums; }
.stat-sub { font-size:11px; color:var(--muted); margin-top:2px; }

.grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px; }
@media(max-width:860px) { .grid-2 { grid-template-columns:1fr; } }

.card {
    background:var(--card); border:1px solid var(--border);
    border-radius:10px; padding:20px; margin-bottom:16px;
}
.card-title {
    font-size:11px; font-weight:600; color:var(--muted);
    text-transform:uppercase; letter-spacing:.06em; margin-bottom:16px;
}
.chart-wrap { position:relative; height:260px; }
.chart-wrap-tall { position:relative; height:340px; }

.tbl { width:100%; border-collapse:collapse; }
.tbl th {
    text-align:left; font-size:11px; text-transform:uppercase;
    letter-spacing:.06em; color:var(--muted); padding:10px 12px;
    border-bottom:1px solid var(--border); white-space:nowrap;
}
.tbl td { padding:10px 12px; border-bottom:1px solid var(--border); vertical-align:middle; }
.tbl tr:last-child td { border-bottom:none; }
.tbl tr:hover td { background:rgba(255,255,255,.02); }
.pts { font-variant-numeric:tabular-nums; font-weight:600; color:var(--accent); }
.cmts { font-variant-numeric:tabular-nums; color:var(--muted); }

.badge {
    display:inline-block; font-size:11px; padding:2px 7px;
    border-radius:4px; font-weight:600; white-space:nowrap;
}
.badge-AIML       { background:rgba(0,180,216,.15);   color:#00b4d8; }
.badge-Programming { background:rgba(157,110,248,.15); color:#9d6ef8; }
.badge-BigTech    { background:rgba(59,130,246,.15);  color:#3b82f6; }
.badge-Security   { background:rgba(239,68,68,.15);   color:#ef4444; }
.badge-Startups   { background:rgba(245,158,11,.15);  color:#f59e0b; }
.badge-Other      { background:rgba(82,82,91,.15);    color:#a0a0b0; }

.rank {
    display:inline-block; width:22px; height:22px; border-radius:4px;
    background:var(--border); text-align:center; line-height:22px;
    font-size:11px; font-weight:700; color:var(--muted);
}
.rank-1 { background:rgba(255,215,0,.2);   color:#ffd700; }
.rank-2 { background:rgba(192,192,192,.2); color:#c0c0c0; }
.rank-3 { background:rgba(205,127,50,.2);  color:#cd7f32; }

.filter-bar {
    background:var(--card); border:1px solid var(--border); border-radius:10px;
    padding:16px 20px; display:flex; flex-wrap:wrap; gap:12px;
    align-items:flex-end; margin-bottom:16px;
}
.filter-group { display:flex; flex-direction:column; gap:5px; }
.filter-label { font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
.filter-input, .filter-select {
    background:var(--surface); border:1px solid var(--border); border-radius:6px;
    color:var(--text); padding:7px 10px; font-size:13px; outline:none; min-width:130px;
}
.filter-input:focus, .filter-select:focus { border-color:var(--accent); }
.btn {
    background:var(--accent); color:#000; border:none; border-radius:6px;
    padding:8px 16px; font-size:13px; font-weight:600; cursor:pointer;
    transition:opacity .15s; white-space:nowrap;
}
.btn:hover { opacity:.85; }
.btn:disabled { opacity:.4; cursor:not-allowed; }
.btn-ghost {
    background:transparent; color:var(--muted); border:1px solid var(--border);
}
.btn-ghost:hover { color:var(--text); border-color:var(--muted); opacity:1; }
.spin { display:inline-block; animation:spin .7s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def badge(cat):
    slug = cat.replace('/', '').replace(' ', '')
    return f'<span class="badge badge-{slug}">{cat}</span>'

def nav_html(active):
    links = [('/', 'Overview'), ('/ai', 'AI / ML'), ('/market', 'Market'), ('/stories', 'Stories')]
    return ''.join(
        f'<a href="{h}" class="nav-link{" active" if h == active else ""}">{l}</a>'
        for h, l in links
    )

def page(title, body, active):
    stories = load_stories()
    dates   = [s['_dt'] for s in stories if s['_dt']]
    last_ts = max(dates).strftime('%b %d %Y, %H:%M') if dates else '—'

    html = (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{title} — HN Intelligence</title>'
        '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>'
        f'<style>{CSS}</style></head><body>'
        '<nav class="nav">'
        '<a href="/" class="nav-brand">&#9632; HN Intelligence</a>'
        + nav_html(active) +
        '<span class="nav-spacer"></span>'
        f'<span class="nav-meta">{len(stories):,} stories &nbsp;&middot;&nbsp; {last_ts}</span>'
        '</nav>'
        '<div class="page">' + body + '</div>'
        '<script>Chart.defaults.color="#6a6a7a";Chart.defaults.borderColor="#22222e";Chart.defaults.font.size=12;</script>'
        '</body></html>'
    )
    return Response(html, mimetype='text/html')

# ── Overview / ────────────────────────────────────────────────────────────────

@app.route('/')
def overview():
    stories = load_stories()
    dates   = [s['_dt'] for s in stories if s['_dt']]
    first_d = min(dates) if dates else None
    last_d  = max(dates) if dates else None

    cat_counts = Counter(s.get('category', 'Other') for s in stories)
    top10      = stories[:10]

    daily = defaultdict(int)
    for s in stories:
        if s['_dt']:
            daily[s['_dt'].strftime('%Y-%m-%d')] += 1
    daily_items = sorted(daily.items())

    # Chart data — serialised once, referenced in JS
    cat_labels = list(CAT_COLORS.keys())
    donut_data = json.dumps({
        'labels': cat_labels,
        'values': [cat_counts.get(c, 0) for c in cat_labels],
        'colors': [CAT_COLORS[c] for c in cat_labels],
    })
    line_data = json.dumps({
        'labels': [d[0] for d in daily_items],
        'values': [d[1] for d in daily_items],
    })

    top10_rows = ''
    for i, s in enumerate(top10, 1):
        rc  = f'rank rank-{i}' if i <= 3 else 'rank'
        top10_rows += (
            f'<tr>'
            f'<td><span class="{rc}">{i}</span></td>'
            f'<td><a href="{s["url"]}" target="_blank" rel="noopener">{s["title"][:92]}</a></td>'
            f'<td class="pts">{s["points"]:,}</td>'
            f'<td class="cmts">{s["comments"]:,}</td>'
            f'<td>{badge(s.get("category","Other"))}</td>'
            f'</tr>'
        )

    ai_pct = f'{cat_counts.get("AI/ML",0)/max(len(stories),1)*100:.0f}%'

    body = f"""
<h1 class="page-title">Market Intelligence Overview</h1>
<p class="page-sub">Hacker News front-page stories &mdash;
{first_d.strftime('%b %d') if first_d else '—'} to {last_d.strftime('%b %d, %Y') if last_d else '—'}</p>

<div class="stats-row">
  <div class="stat-card">
    <div class="stat-label">Total Stories</div>
    <div class="stat-value">{len(stories):,}</div>
    <div class="stat-sub">unique HN IDs</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Date Range</div>
    <div class="stat-value" style="font-size:18px">{first_d.strftime('%b %d') if first_d else '—'}</div>
    <div class="stat-sub">to {last_d.strftime('%b %d, %Y') if last_d else '—'}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Days Tracked</div>
    <div class="stat-value">{len(daily_items)}</div>
    <div class="stat-sub">active scrape days</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">AI / ML Stories</div>
    <div class="stat-value" style="color:#00b4d8">{cat_counts.get('AI/ML',0):,}</div>
    <div class="stat-sub">{ai_pct} of total</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Last Updated</div>
    <div class="stat-value" style="font-size:16px">{last_d.strftime('%b %d') if last_d else '—'}</div>
    <div class="stat-sub">{last_d.strftime('%H:%M') if last_d else '—'}</div>
  </div>
  <div class="stat-card" style="display:flex;flex-direction:column;justify-content:center;gap:8px;">
    <div class="stat-label">Refresh Data</div>
    <button class="btn" id="ref-btn" onclick="doRefresh()">&#8635; Run Scraper</button>
    <div id="ref-status" style="font-size:11px;color:var(--muted)">triggers hn_scraper.py</div>
  </div>
</div>

<div class="grid-2">
  <div class="card">
    <div class="card-title">Category Breakdown</div>
    <div class="chart-wrap"><canvas id="donutChart"></canvas></div>
  </div>
  <div class="card">
    <div class="card-title">Stories Collected Per Day</div>
    <div class="chart-wrap"><canvas id="lineChart"></canvas></div>
  </div>
</div>

<div class="card">
  <div class="card-title">Top 10 Stories &mdash; All Time</div>
  <table class="tbl">
    <thead><tr><th>#</th><th>Title</th><th>Points</th><th>Comments</th><th>Category</th></tr></thead>
    <tbody>{top10_rows}</tbody>
  </table>
</div>

<script>
(function() {{
  var dd = {donut_data};
  new Chart(document.getElementById('donutChart'), {{
    type:'doughnut',
    data:{{ labels:dd.labels, datasets:[{{ data:dd.values, backgroundColor:dd.colors, borderWidth:0, hoverOffset:6 }}] }},
    options:{{ responsive:true, maintainAspectRatio:false, cutout:'65%',
      plugins:{{ legend:{{ position:'right', labels:{{ padding:16, boxWidth:12, color:'#e2e2ea' }} }} }} }}
  }});

  var ld = {line_data};
  new Chart(document.getElementById('lineChart'), {{
    type:'line',
    data:{{ labels:ld.labels, datasets:[{{
      label:'Stories', data:ld.values,
      borderColor:'#00d4a8', backgroundColor:'rgba(0,212,168,.1)',
      borderWidth:2, pointRadius:3, pointBackgroundColor:'#00d4a8', fill:true, tension:0.3
    }}] }},
    options:{{ responsive:true, maintainAspectRatio:false,
      scales:{{
        x:{{ grid:{{display:false}}, ticks:{{color:'#6a6a7a', maxRotation:45}} }},
        y:{{ grid:{{color:'#22222e'}}, ticks:{{color:'#6a6a7a'}}, beginAtZero:true }}
      }},
      plugins:{{ legend:{{display:false}} }}
    }}
  }});
}})();

function doRefresh() {{
  var btn = document.getElementById('ref-btn');
  var st  = document.getElementById('ref-status');
  btn.disabled = true;
  st.innerHTML = '<span class="spin">&#8635;</span> running...';
  fetch('/api/refresh', {{method:'POST'}})
    .then(function(r){{ return r.json(); }})
    .then(function(d) {{
      if (d.ok) {{
        st.textContent = 'done — reloading...';
        setTimeout(function(){{ location.reload(); }}, 1400);
      }} else {{
        st.textContent = 'error: ' + d.error;
        btn.disabled = false;
      }}
    }})
    .catch(function() {{ st.textContent = 'network error'; btn.disabled = false; }});
}}
</script>
"""
    return page('Overview', body, '/')

# ── AI / ML Deep Dive /ai ─────────────────────────────────────────────────────

@app.route('/ai')
def ai_page():
    stories    = load_stories()
    ai_stories = [s for s in stories if s.get('category') == 'AI/ML']

    keywords = ['Claude', 'Anthropic', 'OpenAI', 'GPT', 'LangChain', 'Agent', 'RAG']
    kw_counts = {
        kw: sum(1 for s in stories if re.search(re.escape(kw), s.get('title', ''), re.I))
        for kw in keywords
    }

    weekly_ai  = defaultdict(int)
    weekly_all = defaultdict(int)
    for s in stories:
        if s['_dt']:
            wk = s['_dt'].strftime('%Y-W%V')
            weekly_all[wk] += 1
            if s.get('category') == 'AI/ML':
                weekly_ai[wk] += 1
    all_weeks = sorted(set(list(weekly_ai) + list(weekly_all)))

    kw_data = json.dumps({
        'labels': keywords,
        'values': [kw_counts[k] for k in keywords],
        'colors': ['#00b4d8','#0096c7','#0077b6','#023e8a','#48cae4','#90e0ef','#caf0f8'],
    })
    trend_data = json.dumps({
        'weeks':  all_weeks,
        'ai':     [weekly_ai.get(w, 0)  for w in all_weeks],
        'total':  [weekly_all.get(w, 0) for w in all_weeks],
    })

    ai_rows = ''
    for i, s in enumerate(ai_stories[:60], 1):
        dt = s['_dt'].strftime('%b %d') if s['_dt'] else '—'
        ai_rows += (
            f'<tr>'
            f'<td class="cmts" style="width:32px">{i}</td>'
            f'<td><a href="{s["url"]}" target="_blank" rel="noopener">{s["title"][:95]}</a></td>'
            f'<td class="pts">{s["points"]:,}</td>'
            f'<td class="cmts">{s["comments"]:,}</td>'
            f'<td class="cmts">{dt}</td>'
            f'</tr>'
        )

    body = f"""
<h1 class="page-title">AI / ML Deep Dive</h1>
<p class="page-sub">{len(ai_stories)} AI/ML stories &mdash; keyword frequency and weekly coverage trend</p>

<div class="stats-row">
  <div class="stat-card">
    <div class="stat-label">AI/ML Stories</div>
    <div class="stat-value">{len(ai_stories):,}</div>
    <div class="stat-sub">{len(ai_stories)/max(len(stories),1)*100:.1f}% of all stories</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Claude Mentions</div>
    <div class="stat-value" style="color:#00b4d8">{kw_counts['Claude']}</div>
    <div class="stat-sub">in story titles</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">OpenAI Mentions</div>
    <div class="stat-value" style="color:#9d6ef8">{kw_counts['OpenAI']}</div>
    <div class="stat-sub">in story titles</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Agent Keyword</div>
    <div class="stat-value" style="color:#f59e0b">{kw_counts['Agent']}</div>
    <div class="stat-sub">in story titles</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Anthropic Mentions</div>
    <div class="stat-value" style="color:#00d4a8">{kw_counts['Anthropic']}</div>
    <div class="stat-sub">in story titles</div>
  </div>
</div>

<div class="grid-2">
  <div class="card">
    <div class="card-title">Keyword Frequency in All Titles</div>
    <div class="chart-wrap"><canvas id="kwChart"></canvas></div>
  </div>
  <div class="card">
    <div class="card-title">AI/ML Coverage Trend (Weekly)</div>
    <div class="chart-wrap"><canvas id="trendChart"></canvas></div>
  </div>
</div>

<div class="card">
  <div class="card-title">Top AI/ML Stories by Points</div>
  <table class="tbl">
    <thead><tr><th>#</th><th>Title</th><th>Points</th><th>Comments</th><th>Date</th></tr></thead>
    <tbody>{ai_rows}</tbody>
  </table>
</div>

<script>
(function() {{
  var kd = {kw_data};
  new Chart(document.getElementById('kwChart'), {{
    type:'bar',
    data:{{ labels:kd.labels, datasets:[{{ data:kd.values, backgroundColor:kd.colors, borderRadius:4, borderSkipped:false }}] }},
    options:{{ responsive:true, maintainAspectRatio:false, indexAxis:'y',
      scales:{{
        x:{{ grid:{{color:'#22222e'}}, ticks:{{color:'#6a6a7a'}}, beginAtZero:true }},
        y:{{ grid:{{display:false}}, ticks:{{color:'#e2e2ea'}} }}
      }},
      plugins:{{ legend:{{display:false}} }}
    }}
  }});

  var td = {trend_data};
  new Chart(document.getElementById('trendChart'), {{
    type:'line',
    data:{{ labels:td.weeks, datasets:[
      {{ label:'AI/ML', data:td.ai, borderColor:'#00b4d8', backgroundColor:'rgba(0,180,216,.12)',
         borderWidth:2.5, fill:true, tension:0.3, pointRadius:4 }},
      {{ label:'All Stories', data:td.total, borderColor:'#2a2a3a', borderWidth:1.5,
         fill:false, tension:0.3, pointRadius:2, borderDash:[4,4] }}
    ] }},
    options:{{ responsive:true, maintainAspectRatio:false,
      scales:{{
        x:{{ grid:{{display:false}}, ticks:{{color:'#6a6a7a'}} }},
        y:{{ grid:{{color:'#22222e'}}, ticks:{{color:'#6a6a7a'}}, beginAtZero:true }}
      }},
      plugins:{{ legend:{{ labels:{{ color:'#e2e2ea', boxWidth:12, padding:16 }} }} }}
    }}
  }});
}})();
</script>
"""
    return page('AI/ML Deep Dive', body, '/ai')

# ── Market Intelligence /market ───────────────────────────────────────────────

@app.route('/market')
def market_page():
    stories = load_stories()

    companies = ['Google', 'Meta', 'OpenAI', 'Anthropic', 'Microsoft', 'Nvidia', 'Apple', 'Amazon']
    co_counts = {
        c: sum(1 for s in stories if re.search(r'\b' + re.escape(c) + r'\b', s.get('title', ''), re.I))
        for c in companies
    }
    co_sorted = sorted(companies, key=lambda c: co_counts[c], reverse=True)

    by_cmts = sorted(stories, key=lambda x: x['comments'], reverse=True)[:10]

    weeks_cats = defaultdict(lambda: defaultdict(int))
    for s in stories:
        if s['_dt']:
            wk  = s['_dt'].strftime('%Y-W%V')
            cat = s.get('category', 'Other')
            weeks_cats[wk][cat] += 1
    all_weeks = sorted(weeks_cats)
    CATS = ['AI/ML', 'Programming', 'Big Tech', 'Security', 'Startups', 'Other']

    co_data = json.dumps({
        'labels': co_sorted,
        'values': [co_counts[c] for c in co_sorted],
        'colors': ['#3b82f6','#60a5fa','#93c5fd','#bfdbfe','#1d4ed8','#2563eb','#7c3aed','#a78bfa'],
    })
    weekly_data = json.dumps({
        'weeks': all_weeks,
        'cats':  CATS,
        'series': {cat: [weeks_cats[w].get(cat, 0) for w in all_weeks] for cat in CATS},
        'colors': [CAT_COLORS[c] for c in CATS],
    })

    cmt_rows = ''
    for i, s in enumerate(by_cmts, 1):
        cmt_rows += (
            f'<tr>'
            f'<td class="cmts" style="width:32px">{i}</td>'
            f'<td><a href="{s["url"]}" target="_blank" rel="noopener">{s["title"][:90]}</a></td>'
            f'<td class="pts">{s["comments"]:,}</td>'
            f'<td class="cmts">{s["points"]:,}</td>'
            f'<td>{badge(s.get("category","Other"))}</td>'
            f'</tr>'
        )

    body = f"""
<h1 class="page-title">Market Intelligence</h1>
<p class="page-sub">Company mindshare, discussion leaders, and weekly category trends</p>

<div class="grid-2">
  <div class="card">
    <div class="card-title">Company Mentions in Story Titles</div>
    <div class="chart-wrap"><canvas id="coChart"></canvas></div>
  </div>
  <div class="card">
    <div class="card-title">Weekly Category Breakdown</div>
    <div class="chart-wrap-tall"><canvas id="weeklyChart"></canvas></div>
  </div>
</div>

<div class="card">
  <div class="card-title">Most Discussed Stories (by Comment Count)</div>
  <table class="tbl">
    <thead><tr><th>#</th><th>Title</th><th>Comments</th><th>Points</th><th>Category</th></tr></thead>
    <tbody>{cmt_rows}</tbody>
  </table>
</div>

<script>
(function() {{
  var cd = {co_data};
  new Chart(document.getElementById('coChart'), {{
    type:'bar',
    data:{{ labels:cd.labels, datasets:[{{ data:cd.values, backgroundColor:cd.colors, borderRadius:4, borderSkipped:false }}] }},
    options:{{ responsive:true, maintainAspectRatio:false,
      scales:{{
        x:{{ grid:{{display:false}}, ticks:{{color:'#e2e2ea'}} }},
        y:{{ grid:{{color:'#22222e'}}, ticks:{{color:'#6a6a7a'}}, beginAtZero:true }}
      }},
      plugins:{{ legend:{{display:false}} }}
    }}
  }});

  var wd = {weekly_data};
  var datasets = wd.cats.map(function(cat, i) {{
    return {{ label:cat, data:wd.series[cat], backgroundColor:wd.colors[i], borderRadius:2 }};
  }});
  new Chart(document.getElementById('weeklyChart'), {{
    type:'bar',
    data:{{ labels:wd.weeks, datasets:datasets }},
    options:{{ responsive:true, maintainAspectRatio:false,
      scales:{{
        x:{{ stacked:true, grid:{{display:false}}, ticks:{{color:'#6a6a7a'}} }},
        y:{{ stacked:true, grid:{{color:'#22222e'}}, ticks:{{color:'#6a6a7a'}}, beginAtZero:true }}
      }},
      plugins:{{ legend:{{ position:'bottom', labels:{{ color:'#e2e2ea', boxWidth:12, padding:12 }} }} }}
    }}
  }});
}})();
</script>
"""
    return page('Market Intelligence', body, '/market')

# ── Stories Browser /stories ──────────────────────────────────────────────────

@app.route('/stories')
def stories_browser():
    body = """
<h1 class="page-title">Stories Browser</h1>
<p class="page-sub">Search and filter all collected stories</p>

<div class="filter-bar">
  <div class="filter-group">
    <span class="filter-label">Search Title</span>
    <input type="text" id="q" class="filter-input" placeholder="keyword..." style="min-width:210px">
  </div>
  <div class="filter-group">
    <span class="filter-label">Category</span>
    <select id="cat" class="filter-select">
      <option value="">All Categories</option>
      <option>AI/ML</option><option>Programming</option><option>Big Tech</option>
      <option>Security</option><option>Startups</option><option>Other</option>
    </select>
  </div>
  <div class="filter-group">
    <span class="filter-label">Min Points</span>
    <input type="number" id="pts" class="filter-input" placeholder="0" style="min-width:90px">
  </div>
  <div class="filter-group">
    <span class="filter-label">From</span>
    <input type="date" id="dfrom" class="filter-input">
  </div>
  <div class="filter-group">
    <span class="filter-label">To</span>
    <input type="date" id="dto" class="filter-input">
  </div>
  <button class="btn" onclick="applyFilters()">Apply Filters</button>
  <button class="btn btn-ghost" onclick="clearAll()">Clear</button>
</div>

<div class="card" style="padding:0;overflow:hidden;">
  <div style="display:flex;justify-content:space-between;align-items:center;padding:14px 20px;border-bottom:1px solid var(--border);">
    <span class="card-title" style="margin:0" id="result-count">Loading...</span>
    <span style="font-size:12px;color:var(--muted)">click column headers to sort</span>
  </div>
  <div style="overflow-x:auto;">
    <table class="tbl" id="tbl">
      <thead><tr>
        <th style="cursor:pointer" onclick="sortCol('rank')">Rank</th>
        <th>Title</th>
        <th style="cursor:pointer" onclick="sortCol('points')">Points &#8597;</th>
        <th style="cursor:pointer" onclick="sortCol('comments')">Comments &#8597;</th>
        <th>Category</th>
        <th style="cursor:pointer" onclick="sortCol('date')">Date &#8597;</th>
      </tr></thead>
      <tbody id="tbody">
        <tr><td colspan="6" style="text-align:center;padding:40px;color:var(--muted)">Loading&hellip;</td></tr>
      </tbody>
    </table>
  </div>
  <div style="padding:14px 20px;border-top:1px solid var(--border);display:flex;gap:8px;align-items:center;">
    <button class="btn btn-ghost" id="prev-btn" onclick="changePage(-1)">&#8592; Prev</button>
    <span id="page-info" style="color:var(--muted);font-size:13px;flex:1;text-align:center"></span>
    <button class="btn btn-ghost" id="next-btn" onclick="changePage(1)">Next &#8594;</button>
  </div>
</div>

<script>
var pg = 1, pgSize = 50, total = 0, sortKey = 'points';

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function badgeHtml(cat) {
  var slug = cat.replace('/','').replace(' ','');
  return '<span class="badge badge-'+slug+'">'+esc(cat)+'</span>';
}
function params() {
  return new URLSearchParams({
    q:     document.getElementById('q').value.trim(),
    cat:   document.getElementById('cat').value,
    pts:   document.getElementById('pts').value || 0,
    dfrom: document.getElementById('dfrom').value,
    dto:   document.getElementById('dto').value,
    sort:  sortKey,
    limit: pgSize,
    offset:(pg-1)*pgSize,
  });
}
function load() {
  fetch('/api/stories?' + params())
    .then(function(r){ return r.json(); })
    .then(function(d) {
      total = d.total;
      var tb = document.getElementById('tbody');
      if (!d.stories.length) {
        tb.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:40px;color:var(--muted)">No results.</td></tr>';
        document.getElementById('result-count').textContent = '0 stories';
        document.getElementById('page-info').textContent = '';
        return;
      }
      tb.innerHTML = d.stories.map(function(s){
        return '<tr>'
          +'<td class="cmts">'+(s.rank||'&mdash;')+'</td>'
          +'<td><a href="'+esc(s.url)+'" target="_blank" rel="noopener">'+esc(s.title)+'</a></td>'
          +'<td class="pts">'+s.points.toLocaleString()+'</td>'
          +'<td class="cmts">'+s.comments.toLocaleString()+'</td>'
          +'<td>'+badgeHtml(s.category||'Other')+'</td>'
          +'<td class="cmts" style="white-space:nowrap">'+esc(s.date)+'</td>'
          +'</tr>';
      }).join('');
      var s1 = (pg-1)*pgSize+1, s2 = Math.min(pg*pgSize, total);
      document.getElementById('result-count').textContent = total.toLocaleString()+' stories';
      document.getElementById('page-info').textContent = s1+'–'+s2+' of '+total.toLocaleString();
      document.getElementById('prev-btn').disabled = pg===1;
      document.getElementById('next-btn').disabled = s2>=total;
    });
}
function applyFilters(){ pg=1; load(); }
function clearAll(){
  ['q','pts','dfrom','dto'].forEach(function(id){ document.getElementById(id).value=''; });
  document.getElementById('cat').value='';
  applyFilters();
}
function sortCol(k){ sortKey=k; pg=1; load(); }
function changePage(d){ pg+=d; load(); }
document.getElementById('q').addEventListener('keydown', function(e){ if(e.key==='Enter') applyFilters(); });
load();
</script>
"""
    return page('Stories Browser', body, '/stories')

# ── API endpoints ─────────────────────────────────────────────────────────────

@app.route('/api/stats')
def api_stats():
    stories = load_stories()
    dates   = [s['_dt'] for s in stories if s['_dt']]
    cat_counts = Counter(s.get('category', 'Other') for s in stories)
    keywords   = ['Claude', 'Anthropic', 'OpenAI', 'GPT', 'LangChain', 'Agent', 'RAG']
    kw = {k: sum(1 for s in stories if re.search(re.escape(k), s.get('title',''), re.I)) for k in keywords}

    return jsonify({
        'total_stories': len(stories),
        'date_range': {
            'from': min(dates).isoformat() if dates else None,
            'to':   max(dates).isoformat() if dates else None,
        },
        'last_updated':    max(dates).isoformat() if dates else None,
        'categories':      dict(cat_counts),
        'keyword_frequency': kw,
        'top_10': [
            {'title': s['title'], 'url': s['url'],
             'points': s['points'], 'comments': s['comments'],
             'category': s.get('category')}
            for s in stories[:10]
        ],
    })

@app.route('/api/stories')
def api_stories():
    stories  = load_stories()
    q        = (request.args.get('q') or '').strip().lower()
    cat      = (request.args.get('cat') or '').strip()
    min_pts  = int(request.args.get('pts')   or 0)
    dfrom    = (request.args.get('dfrom') or '').strip()
    dto      = (request.args.get('dto')   or '').strip()
    sort_key = (request.args.get('sort')  or 'points').strip()
    limit    = min(int(request.args.get('limit')  or 50), 200)
    offset   = int(request.args.get('offset') or 0)

    result = stories
    if q:
        result = [s for s in result if q in s.get('title', '').lower()]
    if cat:
        result = [s for s in result if s.get('category') == cat]
    if min_pts:
        result = [s for s in result if s['points'] >= min_pts]
    if dfrom:
        try:
            dt_f = datetime.strptime(dfrom, '%Y-%m-%d')
            result = [s for s in result if s['_dt'] and s['_dt'] >= dt_f]
        except ValueError:
            pass
    if dto:
        try:
            dt_t = datetime.strptime(dto, '%Y-%m-%d').replace(hour=23, minute=59)
            result = [s for s in result if s['_dt'] and s['_dt'] <= dt_t]
        except ValueError:
            pass

    if sort_key == 'comments':
        result = sorted(result, key=lambda x: x['comments'], reverse=True)
    elif sort_key == 'date':
        result = sorted(result, key=lambda x: x['_dt'] or datetime.min, reverse=True)
    elif sort_key == 'rank':
        result = sorted(result, key=lambda x: x['rank'])
    # default: already sorted by points desc

    total = len(result)
    page  = result[offset: offset + limit]

    return jsonify({
        'total': total,
        'stories': [
            {
                'title':    s['title'],
                'url':      s['url'],
                'points':   s['points'],
                'comments': s['comments'],
                'category': s.get('category', 'Other'),
                'rank':     s.get('rank', 0),
                'date':     s['_dt'].strftime('%b %d, %Y') if s['_dt'] else '—',
                'hn_id':    s.get('hn_id', ''),
            }
            for s in page
        ],
    })

@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    try:
        res = subprocess.run(
            ['python', SCRAPER_PATH],
            capture_output=True, text=True, timeout=120
        )
        if res.returncode == 0:
            bust_cache()
            return jsonify({'ok': True, 'output': (res.stdout or '')[-500:]})
        return jsonify({'ok': False, 'error': (res.stderr or 'non-zero exit')[-300:]})
    except FileNotFoundError:
        return jsonify({'ok': False, 'error': 'scraper script not found'})
    except subprocess.TimeoutExpired:
        return jsonify({'ok': False, 'error': 'scraper timed out (>120s)'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    stories = load_stories()
    print(f'Loaded {len(stories):,} unique stories from {CSV_PATH}')
    app.run(debug=True, host='0.0.0.0', port=5001)
