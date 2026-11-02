# Paper evidence inventory

Snapshot: 2026-11-02. Scope: this independent repository and read-only local dependencies. `VERIFIED` means the specified check has evidence; it does not certify an entire strategy. `PROVISIONAL` means usable only with the stated qualification. `MISSING` means no adequate artifact was located.

## Inputs and lineage

| Input | Location and authority | State |
|---|---|---|
| Frozen FMA decision source and config | Read-only `~/FMA_Competition/fma_mpb_v41_20261013/fma_mpb_v41/{momentum_pullback_breakout.py,config.py}`; expected SHA-256 in `configs/mpb_exit_reference.json`. Both hashes matched on 2026-11-02. | VERIFIED source identity; research integration parity PARTIAL |
| Historical signal candidates | `~/FMA_Independent_Research/audit/historical_signal_candidates.csv`; 1,229 rows consumed by `scripts/run_mpb_lifecycle_v5u.py`. The adjacent `signal_differential_summary.json` reports 4,874 comparisons, all 1,229 reported positives, sampled negatives, and seven full dates. | PROVISIONAL for full-universe/full-period parity |
| Market prices and provider action manifest | `~/FMA_Competition/Market_Refresh_Runs/manual_full_20261031T061137Z_432cf6e9/market_bundle/{raw,adjusted,manifest.json}`; external local dependency, absent from this repository. | PROVISIONAL portability and action provenance |
| Curated cash dividends | `configs/verified_cash_dividends.json`, presently modified in the working tree; do not conflate with provider-only inferred dividends. | VERIFIED for registered events; others PROVISIONAL |
| Policy definitions | `protocol/counterfactual_policies_v1.md`, `src/portfolio/risk_budget.py`, `scripts/run_mpb_lifecycle_v4.py`, `scripts/run_mpb_lifecycle_v5u.py`. | VERIFIED implementation inspection; protocol approval pending |

`data/README.md` states that raw data are not distributed. `README.md` and `docs/research_status.md` describe an older blocked pilot and are stale as current status summaries; preserve them as historical snapshots rather than use them for current result claims. `audit/README.md` describes distribution policy, while local ignored `audit/` contains the actual artifacts.

## Final experiment outputs

For each policy `A`, `B`, `C`, the final V5-U source set is `audit/p3_lifecycle_v5u_<policy>_{summary.json,independent_audit.json,daily.csv,trades.csv}`. `audit/p3_abc_v5u_282d_comparison.json` is the aggregate report and records SHA-256 for all twelve source files. `python3 scripts/verify_paper_evidence.py` is a read-only check of those hashes, 282 row counts, endpoints, NAV/return/drawdown and frozen FMA source hashes; it passed on 2026-11-02. `audit/p3_abc_v5u_282_constraints.json` is the end-of-day constraint report. V4 has its own `p3_lifecycle_v4_*` files, `p3_abc_282d_comparison.json`, and `p3_abc_282_constraints.json`; it is a separate contest-capped scenario. The 30-day pilot, diagnostics, and cash-interest shadows are supporting analyses, not replacements for the final comparison.

| Prior check or artifact | Evidence and scope | Audit classification |
|---|---|---|
| V5-U source identity and reported NAV statistics | Twelve hashes and NAV/return/drawdown recomputation matched this review. | PASS |
| V5-U independent accounting replay | Three `p3_lifecycle_v5u_*_independent_audit.json` files report 282/282 sessions and 313/464/478 trades, with cash, NAV, T+1, and receivable identities passing. Their scope says accounting, not strategy validation. | PASS within accounting scope |
| Frozen-source identity | Reference source and config hashes matched `configs/mpb_exit_reference.json`. | PASS |
| Frozen exit decision differential | `audit/mpb_exit_differential.json`: 17/17 synthetic managed-position cases. The user reports 408/408 sampled exit-formula parity elsewhere; no artifact for that count was located in this repository or the inspected local audit directory. | PASS for 17 stored cases; 408/408 is reported context, not independently reverified here |
| Historical signal differential | External `signal_differential_summary.json`: 4,874 checks, all 1,229 reported positives, sampled negatives and seven full sessions. | PARTIAL for full reference signal parity |
| Reference order generation versus research planner | Research runner uses precomputed signal CSV and its own selection, sizing and execution planner. No full differential output was found. | NOT_TESTED |
| V5-U end-of-day constraint replay | `audit/p3_abc_v5u_282_constraints.json`: 282 sessions per policy; observations include budget and sector breaches. Does not certify pretrade or intraday compliance. | PASS for observation; PARTIAL for compliance |
| V4 constraint timing | `audit/p3_constraint_timing_summary.json`: 30 sessions, 15 exception days; different scope from full V5-U. | PARTIAL |
| Corporate actions | `audit/corporate_actions_inventory_summary.json`: 1,952 provider events, including 1,927 provider-only unverified and 23 unmodeled splits across bundle; not all were held. V5-U used 31/43/44 provisional events in A/B/C. | PARTIAL |
| Cash-interest shadow | `audit/p3_cash_interest_scenarios.json`: illustrative arithmetic; no integrated NAV rerun. | PARTIAL |
| StockTrak account reconciliation | Supplementary user-reported context; no transaction-level artifact inspected here. | MISSING as MPB-only performance evidence |

No prior audit file was overwritten. Existing untracked scripts, protocol material, and the modified dividend config predated this review.
