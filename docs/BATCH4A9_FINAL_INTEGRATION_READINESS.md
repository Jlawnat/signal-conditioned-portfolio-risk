# Batch 4A.9 — final integration and experimental readiness

**Decision, 2026-11-02:** The isolated NG-SF-270-LW engine is **PASS in synthetic scope** and **PARTIAL for licensed operational validation**. A controlled, one-policy event-impact diagnostic is **CONDITIONAL GO** after active local-use permission is confirmed. The official 230-session A/B/C/F experiment is **BLOCKED / NO-GO** until the final protocol and private event terms are approved. No historical policy path was run in this batch.

## Integrated path and inspected semantics

The separate `src/portfolio/ng_sf_270_lw_runner_v1.py` accepts a data source and pure feature function. `scripts/run_ng_sf_270_lw_v1.py` supplies a read-only Norgate SQLite source, checks the frozen feature hashes, loads only source-backed verified events, and writes official results only to a versioned Git-ignored `restricted_norgate/ng_sf_270_lw_v1/<run_id>/` directory. An existing output refuses overwrite. Official mode requires a dated approval record matching the exact protocol, data, event register, runner, adapter, action layer, frozen feature and code-manifest hashes. Diagnostic mode writes only a private first-affected-event status, never performance.

The engine uses Norgate membership at T, 270 exactly aligned stock/SPY bars, same-T normalized TOTALRETURN OHLC and CAPITAL volume for signals, raw NONE price/volume economic gates, and raw NONE open/close for fills and marks. Its hard calendar gate is 2025-12-02–2026-10-30, **230 sessions**. The read-only local bridge check returned **230 dates**, endpoints 2025-12-02/2026-10-30 and **503 observed members** on the first date. It was a metadata check, not a policy run. All sector lookups, the 24% cap and Unknown-sector rejection are absent from the new engine. A/B/C preserve the independent V5-U order of MPB exits → overlay → ranked buys, the no-credit-for-pending-sell planner, integer sizing, sell-before-buy execution, 5-basis-point adverse slippage and $10 commission. Optional policy **F** applies B's overlay at a pre-study fixed target; it does not redefine A/B/C.

The journal records S0, S1 (MPB plus overlay), S2 (complete accepted plan), S3 (post-action pre-fill open), S4 (post-fill open) and S5 (next close), with order IDs and a decision-time S2 flush. The 4A.6 reconciler now recognizes a verified split-adjusted pending quantity before comparing it with the fill. Verified dividends, splits and cash-only terminal events pass through the separate action account. An observed action on an active holding/order without registered verified terms, missing terminal price without settlement, unsupported successor/fractional or same-day composite terms, or invalid marks blocks the path. No default settlement or silent omission is used.

## Exact verification

| Check | Result | Evidence |
|---|---|---|
| Integrated S0–S5 no-order path | **PASS** | Synthetic event sequence and two valid zero-gap pairs; order reconciliation PASS. |
| Buy fill, fees, opening/closing NAV | **PASS** | Synthetic raw-opening buy, modeled cost and post-cost NAV; logging-on/off economic results equal. |
| Opening rejection | **PASS** | Synthetic cash rejection terminal in order journal; no fill cost; reconciliation PASS. |
| MPB then B overlay | **PASS** | Synthetic B sells more shares than A after a marked rise; MPB and overlay quantities sum to the combined order. |
| Dividend and payment | **PASS** | Synthetic prior-close entitlement, receivable at ex-date, documented later cash payment. |
| Split and pending order | **PASS** | Synthetic split rebases shares/stop and pending sell; adjusted order quantity reconciles to fill. |
| Terminal and delisted holding | **PASS** | Verified synthetic cash terms convert shares to receivable and cancel pending sell; missing terms/price block. |
| Same-day composite action | **PASS** fail-closed check | Synthetic dividend-plus-split on one active asset blocks without an ordering rule. |
| Forward-information isolation | **PASS** | Changing later raw price and later membership leaves the earlier archived S2 plan identical. |
| Policy C/F calibration | **PASS** | Synthetic C budget varies within 2%–5%; F is constant. Read-only acquired pre-study SPY check gave 165 volatility observations, `σ_ref=0.14485371463395177`, `F=0.03865408095327404`; no policy outcomes used. |
| Read-only Norgate source bridge | **PASS** bounded | Synthetic SQLite membership/raw-row/action-evidence test and acquired calendar metadata check. No full historical runner invocation. |
| Complete licensed-path fidelity and action terms | **PARTIAL** | Actual 230-session policy execution deliberately not run; independent source terms remain absent for potentially material events. |
| Controlled event-impact diagnostic | **CONDITIONAL GO** | Synthetic first-affected-event stop passes; an ignored empty register exists for diagnostic identification only. Confirm active local license before use. No diagnostic was run here. |
| Official Batch 4B | **BLOCKED** | No dated approved protocol or verified material-event register; official approval guard refuses mismatched/missing records. |

`pytest -q tests`: **50 passed, 1 skipped**. Python compilation of the new engine, CLI and modified journal: **PASS**. `git diff --check`: **PASS**. The diagnostic empty register and experiment output namespace are Git-ignored: **PASS**. The skip belongs to the existing test suite; no new 4A.9 test was skipped. There are **no FAIL acceptance tests** in the bounded synthetic scope. These checks do not establish actual Norgate policy outcomes.

## Material event blockers and a narrow path forward

Batch 4A.8's private normalized pre-screen found **2 terminal candidates** with possible entry before terminal pricing and **16 dividend discrepancies** with possible pre-event entry in the later window. These are verification priorities, **not actual holdings**. Held/pending splits and other flagged actions are also potentially material. No new independent real-event terms were verified in 4A.9, and no actual affected A/B/C/F holdings are known because the official run was not executed. The one-policy diagnostic can identify the first event on an actual simulated path without reporting performance; it stops there. Resolve each identified material event with source-backed raw-share terms and payment/settlement dates, or obtain prospective approval for a common pre-event cutoff or separately labeled hypothetical sensitivity. Do not require verification of every event that cannot affect this empty-start design, and do not silently remove a security/date.

## Proposed protocol and approval files

The final [v0.3 approval draft](NG_SF_270_LW_PROTOCOL_V03_APPROVAL_DRAFT.md) fixes the 230-date B–A mean positive common-4% exceedance as the single primary historical contrast, the S2-to-S4 gap and its populations, S3/S4 NAV and cost identities, policy C and pre-study fixed comparator F, a paired circular 20-session block bootstrap (10,000 replicates, seed 20261102; 10/40-block sensitivities), secondary descriptive reporting, and fail-closed missing/action rules. It remains **DRAFT**; none of those choices was selected from new NG-SF-270-LW performance. [Manuscript V3's pre-empirical sections](../paper/MANUSCRIPT_DRAFT_V3_PREEMPIRICAL.md) were updated to describe these proposals without adding results.

Exactly these files/decisions require researcher approval before official mode:

1. `docs/NG_SF_270_LW_PROTOCOL_V03_APPROVAL_DRAFT.md` — approve the complete calendar, primary/secondary analyses, F comparator, uncertainty, and action exception rule; create a dated frozen protocol version.
2. `restricted_norgate/ng_sf_270_lw_verified_events_v1.json` — **not yet created**; privately review and approve independently documented terms for events that may affect held/pending paths. The existing `restricted_norgate/ng_sf_270_lw_diagnostic_empty_events_v1.json` is diagnostic-only and contains no verified terms.
3. `restricted_norgate/ng_sf_270_lw_approval_v1.json` — **not yet created**; record `status=APPROVED`, `approved_on`, and exact `protocol_sha256`, `data_manifest_hash`, `runner_sha256`, `adapter_sha256`, `actions_sha256`, `engine_sha256`, `frozen_feature_sha256`, and `code_manifest_hash`. Official mode validates every field before access to the policy loop.

The manuscript draft needs later research/editorial review, but its present prose is not an approval to run. Any change to approved code, event terms or protocol requires new hashes and a new dated approval record.

## Files touched and next step

Created `src/portfolio/ng_sf_270_lw_runner_v1.py`, `scripts/run_ng_sf_270_lw_v1.py`, `tests/test_batch4a9_runner_synthetic.py`, `docs/NG_SF_270_LW_PROTOCOL_V03_APPROVAL_DRAFT.md`, this report, and private ignored `restricted_norgate/ng_sf_270_lw_diagnostic_empty_events_v1.json`. Modified only `src/portfolio/decision_execution_log_v1.py` to reconcile verified split-adjusted fills and `paper/MANUSCRIPT_DRAFT_V3_PREEMPIRICAL.md` to reflect the proposed methods. Pre-existing working-tree edits were left untouched; frozen FMA, V4/V5-U outputs, old manuscripts and evidence were not overwritten. No official or diagnostic historical policy run, acquisition, commit, push or publication occurred.

Minimum remaining work: review the v0.3 protocol; run a controlled private event-impact diagnostic if licensed use is active; document only economically material event terms or approve a narrower prespecified claim; create the private verified register and dated hash-bound approval; then execute the official versioned policies once, reconcile all files, and write V3 results and discussion without changing the historical V2 record. Full 282-session coverage and WRDS are not required.
