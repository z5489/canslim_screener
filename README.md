# Momentum Stock Stock Screener

A browser-based interactive stock screener that applies Momentum Stock-derived criteria to a pre-screened watchlist. 

Financial data is fetched nightly via 6 staggered GitHub Actions, processed into daily CSV files, and committed back to the repository. The frontend is a static web application that loads the most recent CSV directly to render the results in an interactive, sortable, and filterable table.

---

## Technical Architecture

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
│                                                      │  │
│              rebuild frontend/output/manifest.json            │  │
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

### Screening Criteria

| # | Criterion | Rule | Data Point |
|---|-----------|------|------------|
| 1 | Price vs 52W Low | Current price ≥ 52W low × 1.70 (i.e. +70% above low) | `info['fiftyTwoWeekLow']` |
| 2 | Market Cap | ≥ $300M USD | `info['marketCap']` |
| 3 | EPS Diluted Growth (Quarterly YoY) | > 25% | `quarterly_income_stmt.loc['Diluted EPS']` |
| 4 | Avg Volume 60D | > 500,000 shares | `info['averageVolume']` |
| 5 | Price vs SMA 50 | Current price ≥ 50-day simple moving average | 60-day price history |
| 6 | Volatility 1M | > 3% | Daily range-to-low ratio averaged over last 21 trading bars |
| 7 | Revenue Growth (Quarterly YoY) | > 25% | `quarterly_income_stmt.loc['Total Revenue']` |
| 8 | Float | ≤ 150M shares | `info['floatShares']` |
| 9 | Market | US-listed | Exchange in `{NMS, NYQ, NGM, NCM, ASE, PCX}` |

---

## Directory Structure

```
momentum-stock-screener/
├── .github/
│   └── workflows/
│       ├── batch_1.yml          # GitHub Action workflows staggered by 10 min
│       └── ...
├── data/
│   └── master.csv               # Watch list source of truth (60 popular tickers)
├── scripts/
│   ├── split_master.py          # Utility: split master list into 6 batches
│   ├── fetch_batch.py           # yfinance fetch + criteria evaluation
│   └── merge_output.py          # Merge JSON batch data, update manifest
├── frontend/output/
│   ├── manifest.json            # Dynamic index of all available dates
│   └── output_YYYY-MM-DD.csv    # Daily parsed dataset (schema-aligned)
├── frontend/
│   ├── index.html               # Frontend skeleton
│   ├── style.css                # Premium dark mode stylesheet
│   └── app.js                   # Client-side state, parsing, and rendering
└── tests/
    └── test_screener.py         # Unit tests with yfinance mock objects
```

---

## Getting Started

### 1. Prerequisites
Ensure Python 3.10+ is installed along with the required libraries:
```bash
pip install yfinance pandas numpy
```

### 2. Running Unit Tests
Validate the screener evaluation criteria:
```bash
python tests/test_screener.py
```

### 3. Running Data Pipeline Locally
Run the split utility first:
```bash
python scripts/split_master.py
```

Run fetching for a single batch (1-6):
```bash
python scripts/fetch_batch.py --batch 1 --output data/batch_1.json
```

Merge the fetched batch JSON into today's CSV file and update `manifest.json`:
```bash
python scripts/merge_output.py --batch data/batch_1.json --output-dir frontend/output/
```

### 4. Running the Dashboard
Serve the workspace directory locally:
```bash
python -m http.server 8000
```
Open your browser to `http://localhost:8000/frontend/index.html`.
