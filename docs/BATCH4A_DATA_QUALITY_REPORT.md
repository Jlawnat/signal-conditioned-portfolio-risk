# Batch 4A data quality report

The validator is `python3 scripts/norgate/validate_local.py --db <private.sqlite> --calendar-csv <existing raw SPY.csv> --output <private aggregate.json>`. It exits 0 only when configured hard gates pass. It checks exact 282 ordered unique study dates and SPY alignment, 544 candidate identities, four explicit modes, no padding, full extraction marker, OHLC consistency/nonnegative volume, cross-view date coverage, duplicate primary keys, membership values, member coverage, actual 126-prior-bar sufficiency, transitions, last quoted dates, large raw close moves and capital adjustment-factor jumps. Its private JSON contains checksums and metadata; terminal output prints aggregates only.

The AAPL/delisted sample validation intentionally returned `FAIL` for `sample_extract` and `candidate_count_not_544`; the 282-date calendar itself matched. In that sample all four price views had 1,357 bars each, zero invalid OHLCV, zero duplicate or cross-view mismatches, and no extraction errors. These are sample checks only.

## Full extraction result

The full validator returned **FAIL** solely for `insufficient_126_prior_prices`: 373 member-date observations over five newly listed securities have fewer than 126 preceding price bars. The correct future signal rule is to withhold eligibility until the lookback exists; no bars should be fabricated. The source-file and study-calendar checks passed: 282 exact dates; 544 candidate identities; four views with 244,943 rows each; 0 extraction errors; 0 invalid OHLCV; 0 duplicate price rows; 0 cross-view date mismatches; 0 observed membership gaps or internal price-calendar gaps inside price spans. `NONE` Close matched the `Unadjusted Close` column on all rows, and no negative turnover or zero-volume raw bar was found.

Triage counts are 17 raw close moves above 50% and 15 CAPITAL-to-NONE factor jumps above 1% across the full extracted range; 12 factor jumps occurred in the study window. Twelve capital-event flags occurred in the study window, each on the **prior trading close** to a >1% factor jump, consistent with the documented entitlement alignment. These checks do not prove that every event term or price is correct. The 502/504 membership days, 29 cross-provider dividend amount mismatches and 13 delisted last-bar member cases remain review items; source-level exception details are private.

The private `batch4a_validation_v4_20261102.json` records the restricted SQLite checksum, extractor/validator hashes, acquisition metadata, the 12 exceptional dates, 5 short-history identities, explicit transition dates, terminal series and price-anomaly dates. The private `batch4a_actions_v3_20261102.json` records its own program hash. The extractor's recorded SHA-256 matches the final source file. These local checksums provide reproducibility for this acquisition, subject to Norgate's unversioned source revisions and the active-subscription requirement. The public report omits source-level observations.

## Executed checks

- `python3 scripts/norgate/validate_local.py --db restricted_norgate/batch4a_full_v1_20261102.sqlite --calendar-csv /home/elliot/FMA_Competition/Market_Refresh_Runs/manual_full_20261031T061137Z_432cf6e9/market_bundle/raw/SPY.csv --output restricted_norgate/batch4a_validation_v4_20261102.json` — **FAIL**, only the 126-prior-bar gate, with all other automated hard checks passing.
- `python3 scripts/norgate/audit_actions.py --db restricted_norgate/batch4a_full_v1_20261102.sqlite --legacy-manifest /home/elliot/FMA_Competition/Market_Refresh_Runs/manual_full_20261031T061137Z_432cf6e9/market_bundle/manifest.json --curated configs/verified_cash_dividends.json --output restricted_norgate/batch4a_actions_v3_20261102.json` — executed, 29 dividend discrepancies and terminal cases remain open.
- `/home/elliot/FMA_Independent_Research/.venv/bin/python -m unittest discover -s tests -v` — **19 tests passed**; 408/408 deterministic frozen exit parity cases matched.
- `python3 scripts/verify_paper_evidence.py` — A/B/C stored outputs, 282 dates and frozen FMA source hashes **PASS**. This did not rerun a portfolio.
- `python3 -m py_compile scripts/norgate/windows_extract.py scripts/norgate/validate_local.py scripts/norgate/audit_actions.py`, `git diff --check`, `git check-ignore -v restricted_norgate/batch4a_full_v1_20261102.sqlite` — **PASS**.

No 282-session PIT A/B/C replay or optimization was run. No independently verified merger settlement, all-event payment-calendar or historical sector test could be run from the available sources.

Anomalies require interpretation: a >50% raw close move can be a genuine capital event; a >1% factor jump can be a split or another reconstruction. They are triage counts, not automatic data corrections. Norgate's historical revisions can change future extracts. No raw observation is logged or published.
