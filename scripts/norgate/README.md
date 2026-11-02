# Batch 4A private Norgate extraction

This pipeline uses the installed **Windows** Python and Norgate Data Updater. It writes licensed rows only to ignored `restricted_norgate/`. Do not commit, upload, paste or sync that directory. The output is a separate research input; it is never consumed by the V4/V5-U portfolio runner.

From WSL at this repository root, after confirming the subscription remains active:

```bash
mkdir -p restricted_norgate
python.exe "$(wslpath -w scripts/norgate/windows_extract.py)" --output "$(wslpath -w restricted_norgate)/batch4a_full_v1_20261102.sqlite"
python3 scripts/norgate/validate_local.py --db restricted_norgate/batch4a_full_v1_20261102.sqlite --calendar-csv /home/elliot/FMA_Competition/Market_Refresh_Runs/manual_full_20261031T061137Z_432cf6e9/market_bundle/raw/SPY.csv --output restricted_norgate/batch4a_validation_v1_20261102.json
python3 scripts/norgate/audit_actions.py --db restricted_norgate/batch4a_full_v1_20261102.sqlite --legacy-manifest /home/elliot/FMA_Competition/Market_Refresh_Runs/manual_full_20261031T061137Z_432cf6e9/market_bundle/manifest.json --curated configs/verified_cash_dividends.json --output restricted_norgate/batch4a_actions_v2_20261102.json
```

Replace the versioned output filename on each acquisition. The extractor refuses overwrites. It uses Windows-local temporary SQLite storage because locking a live SQLite database over the WSL UNC share failed in the smoke test, then copies the closed file once. It prints counts and errors, never observations. The validator returns exit code 0 only for a full PASS. A nonzero result can still contain usable anomaly statistics; inspect the ignored JSON and public aggregate report. Date alignment uses the pre-existing study SPY calendar, not a generated weekday list.

If WSL interop fails, in PowerShell from the Windows-accessible repository directory run:

```powershell
python .\scripts\norgate\windows_extract.py --output .\restricted_norgate\batch4a_full_v1_20261102.sqlite
```

Use the existing Windows Python that imports `norgatedata`. Do not reinstall it. The sample command adds `--symbols AAPL,QRVO-202610` and needs a different output name. The `--start` default is 2025-01-02, extending before the first study session for the 126-session lookback; validation counts actual preceding bars for each security. The default end is 2026-10-30. Explicit modes are NONE, CAPITAL, CAPITALSPECIAL and TOTALRETURN, all with `PaddingType.NONE`.

The SQLite file contains `securities`, `prices`, `membership`, `capital_events`, `errors` and acquisition `metadata`. It contains licensed data, including asset IDs and daily membership. The private validation JSON includes exception dates and symbols; terminal output stays aggregate only. Keep both local and private. See [restricted inventory](../../docs/BATCH4A_REPRODUCIBILITY_NOTES.md).
