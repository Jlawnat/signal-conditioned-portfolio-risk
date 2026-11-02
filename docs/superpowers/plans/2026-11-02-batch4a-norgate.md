# Batch 4A Norgate Integration Implementation Plan

> For agentic workers: execute in this session under the user's explicit Batch 4A instruction. Do not commit or spawn subagents.

**Goal:** Build a private, repeatable Norgate extraction and audit without running portfolios or changing frozen research.

**Architecture:** Windows Python writes a SQLite extract under ignored `restricted_norgate/`. WSL Python validates it against the existing SPY research calendar and emits aggregate results. Public documentation records methods, limitations and readiness gates.

**Tech Stack:** Windows Python 3.14, norgatedata 1.0.77, pandas, SQLite, WSL Python standard library.

**Spec:** User's CODEX BATCH 4A request, 2026-11-02.

## Global constraints

- 2025-09-18 through 2026-10-30; 282 study sessions; at least 126 prior trading observations for momentum.
- Explicit NONE, CAPITAL, CAPITALSPECIAL and TOTALRETURN views; no date padding.
- All source rows and daily membership stay private and ignored; no Git commit, push or A/B/C replay.
- Existing V4/V5-U outputs, frozen FMA code and manuscripts remain unchanged.

## Review focus

- Membership arrays can include nonprice dates: keep membership and price coverage separate.
- Delisted symbols can cease trading while membership flags persist: flag each case.
- Capital-event API may ignore requested end date: filter locally to extraction range.
- Indicator availability needs 126 prior valid sessions per asset, not a calendar-year heuristic.
- Adjustment views must not cause cash dividend double counting or infer split terms.

## Tasks

### 1. Bridge and small sample

- [x] Record working tree, inspect prior research, and test Windows Python import from WSL.
- [x] Create standalone extractor with explicit modes and private output protection.
- [x] Run AAPL and one accessible delisted sample; inspect shapes and adjustment behavior.

### 2. Full extract and validator

- [x] Extract 544 watchlist candidates plus SPY to an ignored local SQLite file.
- [x] Validate rows, dates, prices, memberships, identifiers, 126-session lookbacks and event flags against existing SPY calendar.
- [x] Run sample negative-gate validation, then full local validation; full gate FAIL on five genuine short histories.

### 3. Reports

- [x] Write bridge, adjustment, universe, coverage, corporate-action, sector, data quality and reproducibility notes.
- [x] Document restricted inventory, cleanup procedure and unresolved publication gates.
- [x] Verify Git status and existing frozen files remain unchanged.
