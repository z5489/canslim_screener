# CANSLIM Screener — Master Plan & Architecture

---

## 1. Project Summary

A browser-based interactive stock screener that applies CANSLIM-derived criteria to a pre-screened watchlist. Financial data is fetched nightly via GitHub Actions, processed into dated CSV files, and committed to the repo. The frontend is a pure static app — no backend at runtime — that loads the most recent `output_<date>.csv` directly and renders results in a sortable, filterable table with a pass/fail toggle and a date-picker dropdown to browse historical snapshots.

---

## 2. Agreed Requirements

### Input — Data Pipeline
- A `master.csv` of stock tickers is the source of truth
- 6 GitHub Actions workflows split the master list into batches and fetch all CANSLIM data fields for each batch, producing `batch_1.json` … `batch_6.json`
- Each workflow checks whether an `output_<date>.csv` already exists for today; if it does, it merges its batch results in and deduplicates by ticker; if not, it creates it fresh
- The final `output_<date>.csv` accumulates across all 6 batch runs and lives at `frontend/output/output_YYYY-MM-DD.csv`

### Input — Dashboard
- The dashboard is pure frontend — no CSV upload, no backend at runtime
- On load it discovers all available `output_<date>.csv` files, defaults to the most recent, and lets the user switch to older files via a dropdown

### Data Source
- Yahoo Finance via the `yfinance` Python library (no API key required), called inside GitHub Actions

### Screening Criteria

| # | Criterion | Rule | Data Point |
|---|-----------|------|------------|
| 1 | Price vs 52W Low | Current price ≥ 52W low × 1.70 (i.e. +70% above low) | `info['fiftyTwoWeekLow']` |
| 2 | Market Cap | ≥ $300M USD | `info['marketCap']` |
| 3 | EPS Diluted Growth (Quarterly YoY) | > 25% | `quarterly_earnings['Earnings']` |
| 4 | Avg Volume 60D | > 500,000 shares | `info['averageVolume']` |
| 5 | Price vs SMA 50 | Current price ≥ 50-day simple moving average | 60-day price history |
| 6 | Volatility 1M | > 3% | Sum of `(high−low)/|low| × 100` over last ~21 trading bars ÷ bar count |
| 7 | Revenue Growth (Quarterly YoY) | > 25% | `quarterly_financials.loc['Total Revenue']` |
| 8 | Float | ≤ 150M shares | `info['floatShares']` |
| 9 | Market | US-listed | Exchange in `{NMS, NYQ, NGM, NCM, ASE, PCX}` |

### Volatility Formula (TradingView-derived)
```
volatility_1M = sum((high - low) / abs(low) * 100 / N, N)
```
Where `N` = number of trading bars in the last calendar month (~21 trading days). This is a **daily range-to-low ratio**, averaged over the period. Threshold: > 3%.

### Output — Dashboard
- Pure static frontend (HTML + Vanilla JS + CSS), served from GitHub Pages or any static host
- Date dropdown: defaults to most recent `output_<date>.csv`; allows switching to older snapshots
- Sortable, filterable results table
- Each criterion shown as a ✓ or ✗ per stock, with raw value alongside
- **Default view**: only stocks passing ALL criteria
- **Toggle**: "Show all stocks" to reveal partial passes with failed criteria highlighted in red
- Summary bar: total stocks screened, passing count, data date

---

## 3. Architecture

### Full System

```
┌─────────────────────────────────────────────────────────┐
│                     GitHub Repo                         │
│                                                         │
│  master.csv  ──► split into 6 batches                   │
│                        │                                │
│         ┌──────────────┼──────────────┐                 │
│         ▼              ▼              ▼                  │
│   GH Action 1    GH Action 2  … GH Action 6             │
│   (batch_1)      (batch_2)       (batch_6)              │
│         │              │              │                  │
│         └──────────────┼──────────────┘                 │
│                        ▼                                │
│              check frontend/output/output_<date>.csv             │
│              exists? merge + dedup : create             │
│                        │                                │
│              frontend/output/output_YYYY-MM-DD.csv  ◄────────┐  │
│                        │                             │  │
│              committed back to repo                  │  │
└────────────────────────┼─────────────────────────────┘  │
                         │                                 │
              ┌──────────▼──────────┐                      │
              │   Static Frontend   │  fetch() CSV files   │
              │  (GitHub Pages)     │──────────────────────┘
              │                     │
              │  - discover dates   │
              │  - dropdown picker  │
              │  - parse + render   │
              │  - sort / toggle    │
              └─────────────────────┘
```

### File Structure

```
canslim-screener/
├── .github/
│   └── workflows/
│       ├── batch_1.yml          # GH Action for tickers 1–N/6
│       ├── batch_2.yml
│       ├── batch_3.yml
│       ├── batch_4.yml
│       ├── batch_5.yml
│       └── batch_6.yml
├── scripts/
│   ├── fetch_batch.py           # yfinance fetch + criterion eval for one batch
│   ├── merge_output.py          # merge batch JSON into dated CSV, dedup
│   └── split_master.py          # utility: split master.csv into 6 batch files
├── data/
│   ├── master.csv               # source of truth — all tickers
│   ├── batch_1.json             # intermediate (overwritten each run)
│   ├── batch_2.json
│   ├── batch_3.json
│   ├── batch_4.json
│   ├── batch_5.json
│   └── batch_6.json
├── frontend/output/
│   ├── output_2026-05-23.csv    # dated snapshot (one per day)
│   ├── output_2026-05-22.csv
│   └── …
├── frontend/
│   ├── index.html               # single-page app
│   ├── app.js                   # date discovery, CSV parse, table render
│   └── style.css
├── canslim_screener_plan.md
└── README.md
```

---

## 4. GitHub Actions — Data Pipeline

### Trigger
Each of the 6 workflows runs on a shared schedule (e.g. nightly at 02:00 UTC, staggered by 10 minutes to avoid write conflicts) and can also be triggered manually via `workflow_dispatch`.

### Each Workflow — Step by Step

```yaml
# .github/workflows/batch_1.yml
name: Fetch Batch 1
on:
  schedule:
    - cron: '0 2 * * 1-5'   # weekdays 02:00 UTC
  workflow_dispatch:

jobs:
  fetch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install yfinance pandas numpy

      - name: Fetch batch 1 data
        run: python scripts/fetch_batch.py --batch 1 --output data/batch_1.json

      - name: Merge into dated output CSV
        run: python scripts/merge_output.py --batch data/batch_1.json --output-dir frontend/output/

      - name: Commit results
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/batch_1.json output/
          git diff --staged --quiet || git commit -m "chore: update batch 1 $(date +%Y-%m-%d)"
          git push
```

### `fetch_batch.py` — Logic

```python
# scripts/fetch_batch.py
import yfinance as yf, pandas as pd, json, argparse
from concurrent.futures import ThreadPoolExecutor

def fetch_ticker(symbol):
    try:
        t    = yf.Ticker(symbol)
        info = t.info
        hist = t.history(period="3mo")
        earn = t.quarterly_earnings
        fins = t.quarterly_financials
        return evaluate_criteria(symbol, info, hist, earn, fins)
    except Exception as e:
        return {"ticker": symbol, "error": str(e)}

def run(batch_num, output_path):
    master = pd.read_csv("data/master.csv")
    tickers = master["Ticker"].tolist()
    batches = [tickers[i::6] for i in range(6)]   # round-robin split
    batch   = batches[batch_num - 1]

    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(fetch_ticker, batch))

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
```

### `merge_output.py` — Logic

```python
# scripts/merge_output.py
import pandas as pd, json, os
from datetime import date

def run(batch_path, output_dir):
    today     = date.today().isoformat()          # e.g. "2026-05-23"
    out_file  = os.path.join(output_dir, f"output_{today}.csv")

    with open(batch_path) as f:
        batch_data = json.load(f)
    batch_df = pd.DataFrame(batch_data)

    if os.path.exists(out_file):
        existing = pd.read_csv(out_file)
        merged   = pd.concat([existing, batch_df])
        merged   = merged.drop_duplicates(subset="ticker", keep="last")
    else:
        merged = batch_df

    merged.to_csv(out_file, index=False)
```

---

## 5. Output CSV Schema

Each row is one ticker. All criterion raw values and pass flags are stored as flat columns so the frontend needs no computation.

```
ticker, name, price, fetched_at,
c1_price_vs_52w_low_passes, c1_price_vs_52w_low_value,
c2_market_cap_passes,       c2_market_cap_value,
c3_eps_growth_passes,       c3_eps_growth_value,
c4_avg_volume_passes,       c4_avg_volume_value,
c5_price_vs_sma50_passes,   c5_price_vs_sma50_value,
c6_volatility_1m_passes,    c6_volatility_1m_value,
c7_revenue_growth_passes,   c7_revenue_growth_value,
c8_float_passes,            c8_float_value,
c9_us_market_passes,        c9_us_market_value,
passes_all, error
```

`passes_all` = `true` only if all 9 `cN_*_passes` columns are `true` and `error` is empty.

---

## 6. Criterion Implementation Detail

### C1 — Price vs 52W Low (+70%)
```python
price    = info['currentPrice']
low_52w  = info['fiftyTwoWeekLow']
passes   = price >= low_52w * 1.70
value    = f"+{((price / low_52w) - 1) * 100:.1f}%"
```

### C2 — Market Cap ≥ $300M
```python
passes = info['marketCap'] >= 300_000_000
value  = f"${info['marketCap'] / 1e6:.0f}M"
```

### C3 — EPS Diluted Growth Quarterly YoY > 25%
```python
eps    = ticker.quarterly_earnings['Earnings']
growth = (eps.iloc[0] - eps.iloc[4]) / abs(eps.iloc[4])
passes = growth > 0.25
value  = f"+{growth * 100:.1f}%"
```

### C4 — Avg Volume 60D > 500K
```python
passes = info['averageVolume'] > 500_000
value  = f"{info['averageVolume'] / 1e3:.0f}K"
```

### C5 — Price ≥ SMA 50
```python
closes = hist['Close'].tail(50)
sma50  = closes.mean()
price  = closes.iloc[-1]
passes = price >= sma50
value  = f"${price:.2f} / SMA ${sma50:.2f}"
```

### C6 — Volatility 1M > 3%
```python
bars   = hist.tail(21)
N      = len(bars)
vol_1m = ((bars['High'] - bars['Low']) / bars['Low'].abs() * 100 / N).sum()
passes = vol_1m > 3.0
value  = f"{vol_1m:.2f}%"
```
Mirrors the TradingView Pine Script formula: `sum((high−low)/abs(low)*100/bb, bb)`.

### C7 — Revenue Growth Quarterly YoY > 25%
```python
rev    = ticker.quarterly_financials.loc['Total Revenue']
growth = (rev.iloc[0] - rev.iloc[4]) / abs(rev.iloc[4])
passes = growth > 0.25
value  = f"+{growth * 100:.1f}%"
```

### C8 — Float ≤ 150M
```python
passes = info.get('floatShares', float('inf')) <= 150_000_000
value  = f"{info['floatShares'] / 1e6:.1f}M"
```

### C9 — US Market
```python
exchange = info.get('exchange', '')
passes   = exchange in {'NMS', 'NYQ', 'NGM', 'NCM', 'ASE', 'PCX'}
value    = info.get('exchange', 'Unknown')
```

---

## 7. Frontend — Pure Static App

No backend at runtime. The frontend fetches CSV files directly from the repo (via GitHub Pages or raw URLs).

### Date Discovery

The frontend cannot list a directory dynamically, so the repo maintains a small manifest file that is updated by each GitHub Action run:

```
frontend/output/manifest.json
```

```json
{
  "dates": [
    "2026-05-23",
    "2026-05-22",
    "2026-05-21"
  ]
}
```

`merge_output.py` writes/updates `manifest.json` after each successful merge. The frontend fetches `manifest.json` on load, populates the date dropdown, and loads the first (most recent) date's CSV automatically.

### Load Flow

```
1. fetch frontend/output/manifest.json
2. populate date dropdown (most recent selected by default)
3. fetch frontend/output/output_<selected_date>.csv
4. parse CSV (PapaParse)
5. evaluate passes_all per row
6. render table — passing rows only
```

### Date Dropdown Behaviour
- Dropdown label: `Data as of: 2026-05-23 ▾`
- Selecting an older date re-fetches that day's CSV and re-renders the table
- A "last updated" note shows the `fetched_at` timestamp from the CSV

### Table Columns
| Ticker | Name | Price | 52W+70% | Mkt Cap | EPS Q YoY | Vol 60D | Price/SMA50 | Vol 1M | Rev Q YoY | Float | Market | Pass |
|--------|------|-------|---------|---------|-----------|---------|-------------|--------|-----------|-------|--------|------|

- Each criterion cell: raw value + green ✓ or red ✗ badge
- Sortable by any column (click header, toggle asc/desc)
- Default: passing rows only; toggle reveals all

### Toggle
```
[ Passing only ● ]  →  [ All stocks ○ ]
```

### Failure Highlighting
- Failing criterion cells: red tint background + ✗
- Failing rows (in "show all" mode): subtle red left border

### Summary Bar
```
Screened 1,240 stocks  ·  7 passed all criteria  ·  Data: 2026-05-23 06:14 UTC
```

---

## 8. Error Handling

### Pipeline (GitHub Actions)

| Scenario | Behaviour |
|----------|-----------|
| Ticker not found on Yahoo | Row written with `error` field set; all criterion columns N/A |
| Insufficient history (<50 bars) | Affected criteria written as N/A |
| Missing EPS/revenue data (5 quarters needed) | Criterion written as N/A — not a fail |
| Network timeout per ticker | Retry once; then write error row |
| Batch JSON write fails | Action exits non-zero; no partial merge committed |
| Merge conflict (two Actions write simultaneously) | Last writer wins on dedup; stagger cron times to minimise |

### Frontend

| Scenario | Behaviour |
|----------|-----------|
| `manifest.json` not found | Show "No data available yet" message |
| CSV fetch fails | Show error banner with date; prompt to select another date |
| Row has `error` set | Show ticker in muted style with "Data unavailable" tooltip |
| Criterion value is N/A | Cell shows `—` in grey; not counted as pass or fail |

---

## 9. Implementation Phases

### Phase 1 — Data pipeline (scripts)
- `split_master.py` — utility to divide `master.csv` into 6 round-robin batches
- `fetch_batch.py` — yfinance fetch + all 9 criterion functions
- `merge_output.py` — merge batch JSON into dated CSV, update `manifest.json`
- Unit tests for each criterion function

### Phase 2 — GitHub Actions
- 6 workflow YAML files with staggered cron schedules
- `workflow_dispatch` trigger for manual runs
- Commit-back step with bot credentials

### Phase 3 — Frontend
- `index.html` shell + `style.css`
- `app.js`: manifest fetch, date dropdown, CSV parse, table render
- Sort, toggle, summary bar

### Phase 4 — Polish
- Export filtered view to CSV (client-side)
- Column header tooltips explaining each criterion
- Mobile-responsive table (horizontal scroll)
- Highlight newly passing stocks vs previous day (diff against yesterday's CSV)

---

## 10. Dependencies

### Python (GitHub Actions environment)
```
yfinance>=0.2.38
pandas>=2.2
numpy>=1.26
```

### Frontend
- Vanilla JS — no framework, no build step
- PapaParse (CDN) — CSV parsing
- Served as static files via GitHub Pages

### Running the Pipeline Locally
```bash
pip install yfinance pandas numpy

# Fetch one batch
python scripts/fetch_batch.py --batch 1 --output data/batch_1.json

# Merge into today's output CSV
python scripts/merge_output.py --batch data/batch_1.json --output-dir frontend/output/

# Serve frontend
cd frontend && python -m http.server 3000
```

---

## 11. Known Constraints & Risks

| Risk | Mitigation |
|------|------------|
| Two Actions writing the same `output_<date>.csv` simultaneously | Stagger cron by 10 min per batch; dedup on merge keeps last value |
| yfinance rate limiting across 6 concurrent Action runs | Each run uses max 10 workers; Yahoo rate limits per IP, GH Actions uses different IPs per run |
| Quarterly EPS/revenue requires 5 quarters of history | Mark N/A rather than fail; small caps commonly missing this |
| `manifest.json` out of sync | `merge_output.py` always rewrites it atomically after a successful merge |
| Yahoo Finance data quality / staleness | Display `fetched_at` timestamp prominently; note data source in UI |
| GitHub Pages caching of old CSV | Append `?v=<date>` to CSV fetch URLs to bust CDN cache |
| Float data absent for some tickers | Treat as N/A, not a pass; flagged in error column |
