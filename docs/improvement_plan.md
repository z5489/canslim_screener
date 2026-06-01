# Can/Slam Screener - Improvement Plan

## Current State Assessment

### Strengths
- ✅ Modular batch processing (6 batches for rate limit management)
- ✅ Parallel execution with ThreadPoolExecutor
- ✅ Error handling with retry logic for rate limits
- ✅ Schema validation and data normalization
- ✅ Daily output tracking with manifest

### Weaknesses
- ❌ No configuration file (hardcoded thresholds)
- ❌ No logging (only print statements)
- ❌ No caching of yfinance data
- ❌ No unit tests for core logic
- ❌ No CLI automation for full workflow
- ❌ No data validation beyond schema
- ❌ No performance monitoring
- ❌ No API key support for premium data

---

## Improvement Priorities

### Phase 1: Core Infrastructure (High Priority)

#### 1.1 Configuration Management
**Goal**: Make the screener configurable without code changes

**Changes**:
- Create `config.yaml` or `config.json` with:
  - All C1-C9 thresholds
  - Batch size and worker count
  - File paths (data, output, logs)
  - Rate limit settings
- Add `Config` class to load and validate configuration
- Environment variable overrides for sensitive data

**Files to create**:
- `config/default_config.yaml`
- `config/config_manager.py`

**Files to modify**:
- `scripts/fetch_batch.py` - use config instead of hardcoded values
- `scripts/merge_output.py` - use config paths

---

#### 1.2 Logging System
**Goal**: Replace print statements with structured logging

**Changes**:
- Implement Python `logging` module with:
  - File handler (rotating logs)
  - Console handler (with color)
  - Log levels (DEBUG, INFO, WARNING, ERROR)
- Log all API calls, errors, and progress
- Structured JSON logs for analysis

**Files to create**:
- `utils/logger.py`

**Files to modify**:
- `scripts/fetch_batch.py` - replace print with logger
- `scripts/merge_output.py` - replace print with logger

---

#### 1.3 Data Caching
**Goal**: Reduce API calls and improve performance

**Changes**:
- Implement file-based caching for:
  - Ticker info (1-hour cache)
  - Historical data (1-day cache)
- Cache key: `{ticker}_{data_type}_{timestamp}`
- Cache validation before API calls
- Cache statistics in manifest

**Files to create**:
- `utils/cache.py`

**Files to modify**:
- `scripts/fetch_batch.py` - integrate cache in `evaluate_criteria()`

---

### Phase 2: Testing & Quality (Medium Priority)

#### 2.1 Unit Tests
**Goal**: Ensure code correctness and prevent regressions

**Test Coverage**:
- `test_config.py` - Config loading and validation
- `test_cache.py` - Cache operations
- `test_criteria.py` - C1-C9 logic validation
- `test_fetch_batch.py` - Batch processing
- `test_merge_output.py` - Merge logic

**Files to create**:
- `tests/test_config.py`
- `tests/test_cache.py`
- `tests/test_criteria.py`
- Update existing test files

---

#### 2.2 Data Validation
**Goal**: Ensure data quality and detect anomalies

**Changes**:
- Validate ticker data completeness
- Detect and flag suspicious values (e.g., negative revenue)
- Add data quality metrics to output
- Generate validation report

**Files to create**:
- `utils/validator.py`

**Files to modify**:
- `scripts/fetch_batch.py` - add validation step
- `scripts/merge_output.py` - include validation report

---

### Phase 3: User Experience (Medium Priority)

#### 3.1 CLI Automation
**Goal**: One-command execution of full workflow

**Changes**:
- Create `cli.py` with subcommands:
  - `run` - Execute full 6-batch workflow
  - `status` - Show current progress
  - `view <date>` - Display results for a date
  - `export <date> <format>` - Export to different formats
- Add progress bar (tqdm)
- Add summary statistics

**Files to create**:
- `cli.py`

**Files to modify**:
- `scripts/fetch_batch.py` - make reusable as function
- `scripts/merge_output.py` - make reusable as function

---

#### 3.2 Results Dashboard
**Goal**: Easy visualization of screener results

**Changes**:
- HTML dashboard with:
  - Filterable table of results
  - Pass/fail breakdown by criterion
  - Charts (criterion pass rates, price distribution)
  - Export options (CSV, JSON, PDF)
- Auto-generate on each run

**Files to create**:
- `frontend/dashboard.html`
- `frontend/dashboard.js`
- `utils/report_generator.py`

---

### Phase 4: Advanced Features (Low Priority)

#### 4.1 Incremental Updates
**Goal**: Only re-fetch changed tickers

**Changes**:
- Track last fetch time per ticker
- Skip tickers fetched within X hours
- Support "force refresh" option

**Files to create**:
- `utils/incremental.py`

---

#### 4.2 Custom Criteria
**Goal**: Allow users to define custom screening rules

**Changes**:
- JSON-based custom criteria definition
- Python expression evaluator (safe)
- Plugin system for custom criteria

**Files to create**:
- `config/custom_criteria_schema.json`
- `utils/custom_criteria.py`

---

#### 4.3 Email/Notification Alerts
**Goal**: Notify when stocks meet all criteria

**Changes**:
- Compare new results against previous run
- Send email/Discord/Slack notification for new matches
- Configurable notification channels

**Files to create**:
- `utils/notifications.py`

---

## Implementation Timeline

### Week 1: Infrastructure
- [ ] Config management (1.1)
- [ ] Logging system (1.2)
- [ ] Basic caching (1.3)

### Week 2: Testing
- [ ] Unit tests for config/cache (2.1)
- [ ] Data validation (2.2)
- [ ] Integration tests

### Week 3: UX Improvements
- [ ] CLI automation (3.1)
- [ ] Basic dashboard (3.2)

### Week 4: Advanced Features
- [ ] Incremental updates (4.1)
- [ ] Custom criteria (4.2)
- [ ] Notifications (4.3)

---

## Technical Debt to Address

1. **Hardcoded paths**: Move all paths to config
2. **Magic numbers**: Extract all thresholds to config
3. **Error handling**: Standardize error types and messages
4. **Type hints**: Add type annotations to all functions
5. **Docstrings**: Add comprehensive documentation
6. **Code duplication**: DRY up common patterns

---

## Dependencies to Add

```txt
# config
pyyaml>=6.0
python-dotenv>=1.0

# logging
# (built-in, no change needed)

# caching
# (built-in, no change needed)

# testing
pytest>=7.0
pytest-cov>=4.0
pytest-asyncio>=0.21

# CLI
click>=8.0
tqdm>=4.65

# data validation
pydantic>=2.0

# reporting
jinja2>=3.1
reportlab>=4.0
```

---

## Success Metrics

- **Performance**: 50% reduction in API calls (via caching)
- **Reliability**: 95%+ test coverage
- **Usability**: Full workflow in 1 command
- **Maintainability**: All code documented and typed
- **Flexibility**: All thresholds configurable without code changes

---

## Notes

- Start with Phase 1 improvements as they provide immediate value
- Test changes incrementally after each phase
- Maintain backward compatibility where possible
- Document all breaking changes
- Consider adding a `CHANGELOG.md` for tracking
