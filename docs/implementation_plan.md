# Implementation Plan — CANSLIM Screener

Implement an interactive browser-based stock screener applying CANSLIM-derived criteria. Financial data is fetched nightly via GitHub Actions, processed into dated CSV files, and committed to the repository. The frontend is a static web application that parses the CSV files using PapaParse and displays the results in a premium, sortable, and filterable table.

## User Review Required

> [!IMPORTANT]
> **Financial Data API (yfinance)**
> We are using the `yfinance` library to fetch stock information. The library fetches data directly from Yahoo Finance without requiring an API key. 
> To support YoY growth calculations for EPS and Revenue:
> - `quarterly_earnings` is deprecated in yfinance and returns `None`. We have verified that `t.quarterly_income_stmt` is the correct source, containing `Diluted EPS` and `Total Revenue` rows across 5 quarters (permitting a YoY comparison of the current quarter with the 4th preceding quarter).
> - If a stock has insufficient history (e.g. less than 50 trading days or less than 5 quarters of financial reports), the affected criteria are set to `N/A` (which displays as `—` and is treated as a non-pass).

> [!NOTE]
> **Data Splits & Deduping**
> - The 60-ticker master watch list is split using a round-robin scheme into 6 batches (10 tickers each).
> - Staggering the GitHub Actions runs by 10 minutes (or running them sequentially) will prevent write/commit conflicts. The merge script uses `pandas` to read/update the dated CSV file and the `manifest.json` index, ensuring atomic updates.

## Open Questions

None at this time. The plan matches the specification in [plan.md](file:///c:/Users/ziyen/canslim_screener/docs/plan.md) and has been validated against active Yahoo Finance data.

---

## Proposed Changes

### Component 1: Python Pipeline & Data Config

This component handles fetching data from Yahoo Finance, evaluating CANSLIM criteria, and merging the outputs into a CSV daily.

#### [NEW] [master.csv](file:///c:/Users/ziyen/canslim_screener/data/master.csv)
- Store the master watchlist of 60 popular US tickers.

#### [NEW] [split_master.py](file:///c:/Users/ziyen/canslim_screener/scripts/split_master.py)
- Utility script to split `data/master.csv` into 6 files (`batch_1.json`, etc.) or dynamically run on a single batch.

#### [NEW] [fetch_batch.py](file:///c:/Users/ziyen/canslim_screener/scripts/fetch_batch.py)
- Fetches yfinance data for a given batch.
- Contains the 9 CANSLIM evaluation criteria.
- Handles errors, missing data, and type-converts numpy data types to standard JSON-serializable types.

#### [NEW] [merge_output.py](file:///c:/Users/ziyen/canslim_screener/scripts/merge_output.py)
- Merges the batch JSON output into the dated CSV `output/output_YYYY-MM-DD.csv`.
- Deduplicates tickers, keeping the latest fetched data.
- Updates `output/manifest.json` with the list of dates sorted descending.

---

### Component 2: GitHub Actions Workflows

Automate the nightly runs and support manual triggering.

#### [NEW] [.github/workflows/batch_1.yml](file:///c:/Users/ziyen/canslim_screener/.github/workflows/batch_1.yml) ... [.github/workflows/batch_6.yml](file:///c:/Users/ziyen/canslim_screener/.github/workflows/batch_6.yml)
- Nightly triggers at 02:00, 02:10, 02:20, 02:30, 02:40, 02:50 UTC respectively.
- Manual execution trigger (`workflow_dispatch`).
- Commits results back to the repo using a GitHub Actions bot.

---

### Component 3: Premium Static Frontend

A beautiful frontend with dynamic controls.

#### [NEW] [index.html](file:///c:/Users/ziyen/canslim_screener/frontend/index.html)
- Main HTML structure.
- Imports Google Fonts (Inter) and Tailwind CSS / custom styles.
- Loads PapaParse CDN and the main frontend logic.

#### [NEW] [style.css](file:///c:/Users/ziyen/canslim_screener/frontend/style.css)
- Custom premium styling (modern dark-theme, glassmorphism, responsive table, animated tooltips, passing/failing badges).

#### [NEW] [app.js](file:///c:/Users/ziyen/canslim_screener/frontend/app.js)
- Fetches `output/manifest.json` and loads the latest CSV.
- Populates the date picker.
- Implements sorting, filtering (Toggle "Passing only" / "All"), search, and client-side CSV export.
- Features custom tooltips on hover for column headers to explain each criterion.
- Displays a summary bar (total screened, passing count, last update timestamp).

---

## Verification Plan

### Automated Tests
- We will write a test suite in Python (`tests/test_screener.py`) to verify each criterion logic using mock yfinance objects.
- Command to run: `python -m unittest tests/test_screener.py`

### Manual Verification
1. Run `split_master.py` to check batch generation.
2. Run `fetch_batch.py` for batch 1 to verify fetch and criterion evaluation.
3. Run `merge_output.py` to merge batch 1 and update `manifest.json`.
4. Run a local web server: `cd frontend && python -m http.server 3000`.
5. Open browser at `http://localhost:3000` to verify:
   - Date selection dropdown.
   - Screened vs passing counts.
   - Pass/fail highlights and toggle.
   - Interactive sorting and searching.
   - Client-side CSV export of filtered data.
