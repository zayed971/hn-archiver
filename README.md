# HN Market Intelligence

A Hacker News front-page scraper and analytics dashboard that tracks AI industry trends, company mindshare, and community engagement patterns across thousands of stories.

---

## What It Is

An automated data pipeline that captures the Hacker News front page on a recurring schedule and stores every story — title, points, comments, category, rank, and timestamp — into a structured CSV archive. A Flask web dashboard then turns that raw data into interactive charts and a searchable story browser.

**Four dashboard views:**
- **Overview** — high-level stats, category donut chart, stories-per-day trend
- **AI/ML Deep Dive** — keyword frequency (Claude, Anthropic, OpenAI, GPT, Agent…), weekly coverage trends
- **Market Intelligence** — company mindshare rankings, most-discussed stories, weekly category breakdown
- **Stories Browser** — searchable, filterable table of every collected story with live pagination

---

## Why It Matters

Hacker News is the closest thing the tech industry has to a real-time intelligence feed. The top 30 stories at any moment represent what 10 million engineers, founders, and researchers collectively find most important. Tracking this over time surfaces:

- Which AI companies dominate mindshare (and how fast the gap is closing)
- Whether AI coverage is accelerating or plateauing
- What kinds of stories generate the most discussion vs. the most upvotes
- Macro shifts in what the tech community cares about week-over-week

---

## Key Findings (March – April 2026)

| Signal | Count |
|---|---|
| **Claude** mentions in titles | **35×** |
| **Agent** keyword in titles | **41×** |
| **OpenAI** mentions | 18× |
| **Anthropic** mentions | 10× |
| AI/ML share of front page | ~20% of all stories (240 / 1,173) |
| Most-discussed story | 900+ comments |

Claude dominated AI keyword mentions by a significant margin over the period, driven by Claude Code launches, security research disclosures, and community tool releases. The "Agent" keyword surged in the final weeks, suggesting a narrative shift from base models toward agentic applications.

---

## Tech Stack

| Layer | Tech |
|---|---|
| Scraping | Python · `requests` · HN Algolia API or HTML parse |
| Storage | CSV flat file (`hn_archive.csv`) |
| Backend | Python · Flask 3 |
| Charts | Chart.js 4 (CDN) |
| Styling | Pure CSS — dark minimal, no frameworks |
| API | REST JSON (`/api/stats`, `/api/stories`) |

---

## How to Run

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Ensure data is present**

`hn_archive.csv` should be in the same directory as `web_dashboard.py`.

**3. Start the dashboard**
```bash
python web_dashboard.py
```

Open [http://localhost:5001](http://localhost:5001)

**4. Collect new data**

Run the scraper manually or click the **Refresh** button on the dashboard:
```bash
python hn_scraper.py
```

---

## Project Structure

```
hn_archiver/
├── hn_archive.csv       # Raw collected data (~1,800+ rows)
├── hn_scraper.py        # Data collection script
├── web_dashboard.py     # Flask dashboard (single file, self-contained)
├── requirements.txt
└── README.md
```

---

## API

### `GET /api/stats`
Returns a JSON summary of the entire dataset — total stories, date range, category breakdown, keyword frequencies, and the top 10 stories. Useful as a portfolio API endpoint.

```json
{
  "total_stories": 1247,
  "date_range": { "from": "2026-03-17T09:45:00", "to": "2026-04-05T07:20:00" },
  "categories": { "AI/ML": 271, "Programming": 198, "Other": 634, ... },
  "keyword_frequency": { "Claude": 48, "Agent": 26, "OpenAI": 18, ... },
  "top_10": [ ... ]
}
```

### `GET /api/stories`
Paginated, filterable story list.

| Param | Description |
|---|---|
| `q` | Title keyword search |
| `cat` | Category filter |
| `pts` | Minimum points |
| `dfrom` / `dto` | Date range (YYYY-MM-DD) |
| `sort` | `points` · `comments` · `date` · `rank` |
| `limit` | Max results (≤ 200, default 50) |
| `offset` | Pagination offset |

---

## Screenshots

> *(Add screenshots after first run — Overview, AI/ML, and Stories Browser are the most visual)*

---

## Author

Zayed Zaidan · AI Engineering student · [GitHub](https://github.com/zayed971)
