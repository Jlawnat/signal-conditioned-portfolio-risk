# Batch 4A.7 execution log — 2026-11-02

## Authorized scope and access

Initial managed WSL access returned Wsl/E_ACCESSDENIED. Approved elevated local access succeeded; no remote data processing was used. `rg` is absent in Ubuntu, so bounded find/grep and source reads were used. No new package or key was installed, no purchase or trial extension requested.

## Exact meaningful commands and outcomes

From /home/elliot/signal-conditioned-portfolio-risk:

1. `python.exe "$(wslpath -w scripts/norgate/windows_extract.py)" --start 2023-01-01 --output "$(wslpath -w restricted_norgate)/batch4a7_warmup_v1.sqlite"`: completed **545/545** identities. This requests earlier history but does not bypass the two-year trial limit. Four modes each **266,468** rows; zero extraction errors in subsequent validation.
2. `/home/elliot/FMA_Independent_Research/.venv/bin/python scripts/norgate/batch4a7_clearance.py --db batch4a7_warmup_v1.sqlite --output batch4a7_clearance_v2.json`: **exit 0**, bounded audit completed; explicit READY_FOR_4B=false. Exit 0 means report completion, not Data Clearance. Actual results and limitations are in BATCH4A7_DATA_CLEARANCE.md.
3. `python3 scripts/norgate/validate_local.py --db restricted_norgate/batch4a7_warmup_v1.sqlite --calendar-csv /home/elliot/FMA_Competition/Market_Refresh_Runs/manual_full_20261031T061137Z_432cf6e9/market_bundle/raw/SPY.csv --output restricted_norgate/batch4a7_validation_v2.json`: **exit 0; structural PASS; issues=[]; ready_for_4b=false**. 282 dates, 544 candidates; zero invalid OHLCV, duplicates, cross-view mismatches and extraction errors. 373 observations/five securities below 126 prior bars remain a signal qualification diagnostic. Missing membership observations after terminal bars are not independently cleared.
4. `python3 -m pytest -q tests/test_batch4a7_clearance.py tests/test_batch4a6_synthetic.py`: **11 passed in 0.27s**, exit 0. Earlier temporary five-test version passed alongside seven 4A.6 tests; a source-string test was removed as low-value. Final suite is four meaningful qualification/comparison tests plus seven prior synthetic execution tests.
5. `python3 -m py_compile scripts/norgate/batch4a7_clearance.py scripts/norgate/validate_local.py`: **exit 0**.
6. `python3 scripts/verify_paper_evidence.py`: **exit 0**. Existing A/B/C each have 4 verified hashes and 282 sessions; stored fills 313/464/478 respectively, with NAV/return/drawdown PASS. Frozen FMA: **2 source hashes PASS**. This reads existing results, does not replay them.
7. `git diff --check`: **exit 0**. `git check-ignore restricted_norgate/batch4a7_clearance_v2.json restricted_norgate/batch4a7_warmup_v1.sqlite`: both ignored, exit 0.

First attempted pytest in the existing research virtualenv returned `No module named pytest`; used existing system Python successfully without installation. Provisional private audit v1 used the wrong signal key and is superseded; final v2 uses `entry_confirmed` with a schema assertion. Neither provisional terminal conclusion nor a PASS-only structural report may authorize 4B.

## Changed files

New: scripts/norgate/batch4a7_clearance.py; tests/test_batch4a7_clearance.py; docs/BATCH4A7_DATA_CLEARANCE.md; docs/BATCH4A7_NORGATE_ONLY_VARIANT_V01_DRAFT.md; this log.

Modified: scripts/norgate/validate_local.py only (classification of IPO warmup versus structural data error, explicit narrow scope and false 4B readiness). Existing modified configs/verified_cash_dividends.json and untracked paper tables/prior docs/plans were preserved. No existing protocol, manuscript, runner, frozen FMA, V4/V5-U output, commit or push was changed or executed. New private artifacts are listed in the clearance report; never stage or publish them. No formal 282-session A/B/C PIT run occurred.

## Next permitted work

Continue private event evidence collection and a future independent adapter/accounting implementation. NG-SF-270-LW v0.1 is an unfrozen sector-free later-window design proposal. Do not start 4B until every material gate is resolved or covered by a documented approved alternative and dated protocol approval. Exact trial expiry must be checked by the researcher; no date was guessed or automatic deletion scheduled.
