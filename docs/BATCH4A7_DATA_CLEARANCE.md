# Batch 4A.7 Norgate-only Data Clearance — 2026-11-02

**Decision: PARTIAL clearance; protocol freeze and Batch 4B remain BLOCKED.**
This is a bounded local audit, not a portfolio replay or a V3 manuscript revision. WRDS is deferred. No historical result becomes independent out-of-sample evidence through a provider change. Existing protocols and manuscripts remain unchanged.

## Executed evidence

Read the seven Batch4A readiness/quality/coverage/actions/adjustment/reproducibility/sector documents, Publication Protocol V2 and Amendment 01, Windows extractor, validator, action auditor, Batch4A.6 implementation audit, and logged runner. Inspected frozen feature code read-only and verified configured source hashes before extracting its pure feature functions. Preserve pre-existing changes in configs/verified_cash_dividends.json, two paper table JSONs, draft logging specification and prior plan.

The source signal has `CFG.min_history=270`: both stock and SPY need 270 aligned valid OHLCV bars through T. The earlier 126-prior-bar test alone was insufficient. The original January-2025-start extract produced 46,712 warmup-constrained member dates over 516 identities. This is extraction truncation for mature stocks, not an IPO fact. An independent Windows/Norgate extraction now starts 2023-01-01, ends 2026-10-30, uses all four explicit modes and NONE padding, and is stored only in restricted_norgate/batch4a7_warmup_v1.sqlite. No subscription purchase, new key or package installation was used.

Final local audit aggregates:

```json
{
  "membership_exception_dates": 12,
  "warmup": {
    "PIT_ELIGIBLE_NO_SIGNAL_WARMUP": 26686,
    "HISTORY_READY_NOT_SIGNAL_PROVEN": 115160,
    "member_dates_lt126_prior": 373
  },
  "warmup_affected_securities": 512,
  "dividend_exceptions": 29,
  "dividend_hypotheses": {
    "mode_match_hypotheses": 12,
    "capital_factor_normalization_hypotheses": 12
  },
  "independently_cleared_dividends": 0,
  "delisted_candidates": 16,
  "last_bar_member_one": 15,
  "terminal_candidates_with_possible_feature_entry": 2,
  "actual_PIT_holdings_verified": false,
  "READY_FOR_4B": false
}
```

Structural validator: PASS; extraction errors 0; invalid OHLCV 0; cross-view mismatches 0. A structural PASS is explicitly **not** Data Clearance, signal availability certification, or permission to run 4B.

## Membership: 12 dates

The ignored v2 audit contains all observed identities for each exceptional date, neighboring-session additions/removals, flags, and possible terminal/missing-member candidates. This addresses the actual securities locally without publishing licensed membership sets. Do not force counts to 503. Neither no-padding prices nor their aligned flags independently establish that a halted or terminated member is absent. Share-class identity, official effective dates and index-provider handling remain unverified: observed flag dates are not independent effective-date evidence.

Norgate's public FAQ says daily effective-date membership is provided, but temporary inclusions are intentionally omitted and announcement dates are absent. Thus this is specifically the **Norgate daily constituent definition**, not a certified reconstruction of every temporary official index line. Remaining work is a private identity/event review with independent public index notices where available, plus an independent membership coverage test across terminal/halts. The event matrix marks these fields unknown instead of inventing share classes or dates. Status PARTIAL, material.

## Signal qualification

Keep `PIT_member=1` separate from `signal_ready`. A new listing with fewer than 126 actual preceding valid bars is `PIT_ELIGIBLE_NO_SIGNAL`, never a corrupt member or a silently deleted constituent. No padding, fabricated pre-listing bars, or future-history counting is permitted. Actual feature entry requires 270 bars including T with exact stock/SPY date alignment, coherent positive OHLCV and the frozen indicator inputs. Stock and benchmark must be physically truncated at T. Missing internal bars, malformed values and mismatched dates are data/availability problems, not automatically excused as IPO warmup.

Use the earliest date at which those actual requirements are met; never choose the start date from later returns or successful trades. Fetch earlier history for mature securities before interpreting missing warmup as economic ineligibility. Recompute status from the acquired as-of slice, record first-ready dates privately, and enforce identical qualification for A/B/C. Entry eligibility alone does not imply an order or fill.

`validate_local.py` now retains the 373/5 diagnostics as signal constraints instead of a structural data-error hard failure, preserves all other hard gates, declares its narrow scope and always reports `ready_for_4b=false`. Detailed 270-bar counts are in the independent audit. No existing runner or frozen strategy was changed.

## 29 dividend exceptions

Every original exception is retained in the ignored v2 audit, with stable ID, original comparator amount, prior observed entitlement date, exact ex-date availability, adjacent raw rows, all four same-date mode rows, CAPITAL/NONE factor, numeric matches and CAPITAL versus CAPITALSPECIAL residual. Entitlement is prior close, not payment or record date. If the next observed date is not the stated ex-date, this is explicitly unresolved.

Numeric mode/factor matches are **hypotheses**; none is independently cleared. A close adjustment factor is not proof of the split ratio or dividend unit convention. Ordinary/special residuals do not establish legal distribution character, record date or cash payment. All 29 retain null independent terms/record/payment dates. Existing curated USB/CAT evidence remains separate. Never fabricate a replacement amount. Next: source issuer/exchange documents for material reachable events, establish share units across splits and special distributions, then match original vendor amount/date. Missing payment information blocks reinvestable cash accounting even when entitlement agrees.

## 16 terminal candidates and the 13 last-bar members

The audit tests the actual frozen pure feature function on truncated TOTALRETURN stock/SPY panels for each terminal candidate, only on eligible member decision dates before its terminal price date, after source-hash validation. It does not call the logged runner, rank the whole universe, allocate capital or execute A/B/C paths. Per-security results stay private. The 13 last-bar members are explicitly marked; two candidates lacking bars in the earlier extract are reconsidered with extended history.

A qualifying signal means **possible entry**, not actual holdings. Ranking, slots, cash, risk budgets, costs and exits are path dependent. A no-entry finding applies only to an empty-start path under this precise extract and frozen feature mapping; revised histories, normalized signal views or different warmup invalidate it. No event is waived on that basis for a different design. Actual PIT holdings remain UNKNOWN. For every potentially reachable terminal holding, record an independently documented cash/share consideration, effective date, settlement timing, successor identity and fractional-share treatment, or fail closed. Held/pending splits also need tested quantity/stop/order adjustment, currently unsupported by the logged executor. Never assume sale at the final close, forward-fill a sale, silently drop a holding or set its economic value to zero. A zero-recovery stress case could be a separately labeled sensitivity, never verified settlement.

## Accounting recommendation, not executor certification

Use NONE raw open for T+1 fills and NONE close for marks in real share units. Maintain raw quantities, cash and separate receivables. Accrue a verified cash distribution only for shares entitled at prior close; move receivable to cash only on documented payment date, with no cash-before-payment reinvestment. Confirm whether NONE's dividend is raw per-share before using it; CAPITAL amounts cannot be assumed raw. Verified splits adjust quantities and all unit-dependent stops/pending orders exactly once on the documented effective date; splits create no free NAV. Special cash and stock distributions require event-specific terms, not automatic ordinary-dividend treatment.

TOTALRETURN is signal-only; CAPITAL and CAPITALSPECIAL are reconciliation/sensitivity views. Do not credit distribution cash on top of TOTALRETURN NAV marks, use CAPITALSPECIAL marks plus special cash twice, or infer corporate-action terms solely from factors. Convert a signal stop to raw T units with a same-T factor and preserve/rebase it only through documented actions. Current-vintage adjusted prices can contain later scaling; physical truncation alone does not prove vintage PIT correctness for absolute-price or volume thresholds. The separate variant draft requires decision-date normalization and raw economic gates, with tested factor invariance, before freeze.

## Data Clearance matrix and 4B entry gates

| Item | Status | Materiality | Necessary next step |
|---|---|---|---|
| Local access, four modes, structural extraction | VERIFIED within checks | High | Freeze acquisition/validator hashes privately; structural PASS alone insufficient |
| 126-day IPO semantics and 270-bar rule discovery | VERIFIED | Critical | Implement same as-of rule in future input adapter; maintain members with no signal |
| Expanded history acquisition | VERIFIED as acquired, not historical vintage | Critical | Review remaining qualification/coverage and valid OHLCV, aligned dates |
| Twelve exceptional membership dates/classes | PARTIAL | High | Independent effective-date/class review; terminal/halts coverage and temporary-line definition |
| 29 cross-provider dividends | PARTIAL | High | Independent terms, share-unit match, record/payment dates; no numeric-only clearance |
| Capital actions and quantity/stop/order ledger | BLOCKED | Critical | Verified ratios/event terms and synthetic NAV/unit accounting tests |
| Terminal actual holding/settlement exposure | PARTIAL / BLOCKED | Critical | Retain private reachability list; resolve all potentially reachable settlements and prove adapter behavior |
| Historical sector data for original 24% strategy | BLOCKED | Critical for original | Original cannot be replicated with current classifications; WRDS deferred |
| Sector-free Norgate variant | PARTIAL draft | High | Review separate design, normalized signal/economic gates and claims; never overwrite original |
| Decision/execution instrumentation | VERIFIED synthetic scope only | High | Existing 4A.6 synthetic tests pass; validate new adapter/actions before replay |
| Estimand/statistics/C comparator/denominator | PARTIAL | High | Prespecify dependence-aware method, multiplicity and comparator before results |
| License expiration and retained artifacts | PARTIAL operational | Critical | Confirm actual expiration date privately; inventory all copies and execute cleanup on expiry |
| Freeze protocol / start Batch4B | BLOCKED | Critical | All material gates resolved or explicit independently reviewed design alternative, then dated approval |

4B requires a new versioned protocol, exact private input hashes, stable security joins, membership semantics, as-of feature/price validation, action and terminal ledger, executor unit tests including pending orders, S0-S5 reconciliation, fixed start state/calendar/costs, estimands and comparison scope, predeclared C comparator and uncertainty method, dated researcher approval, and active data permission. No official 282-day run is authorized by this report.

## Reproducibility, verification and corrections

Added scripts/norgate/batch4a7_clearance.py, tests/test_batch4a7_clearance.py and these two new docs; modified only independent scripts/norgate/validate_local.py. Tests: `python3 -m pytest -q tests/test_batch4a7_clearance.py tests/test_batch4a6_synthetic.py` => **11 passed in 0.27s**. Four tests cover the 269/270 boundary, future-bar exclusion, equal-count misalignment and amount comparison/missing values; seven retain Batch4A.6 execution-loop tests. The research virtualenv lacks pytest; the successful tests used existing system Python, without installing anything. Audit analysis uses the existing research virtualenv's pandas/numpy. Compile and diff checks are recorded in the accompanying execution log. No formal replay, optimization, manuscript change, commit or push occurred.

Private v1 audit is **superseded**: its terminal-feature predicate initially looked for `eligible`; inspection found the actual returned key is `entry_confirmed`. Corrected before the extended-history v2 run, with a fail-closed schema assertion. Do not use the provisional zero-entry v1 conclusion. The original 46,712/516 warmup diagnostic is unaffected. No source rows or per-security output were printed or submitted to remote services.

## Expiration obligation — correction to prior wording

The current EULA (20261002), clauses 2 and 21, permits subscription-period personal processing and requires cessation/deletion of relevant Content on expiration, including exports, extracts and backups across processing environments. The prior report's imminent-renewal exception is not present in that text and must not be relied upon without applicable written authorization. Keep only material actually qualifying as Derived Data; do not assume aggregate data-audit tables qualify. Inventory old/new SQLite extracts, detailed audits, snapshots, temporary exports, backups and sync copies. If no active subscriptions remain, the agreement also calls for deletion of Software and Documentation. No automatic deletion was performed; exact trial expiration is not inferred from “three weeks”.

Public sources checked 2026-11-02: [Norgate Data FAQ](https://norgatedata.com/data-package-faq.php), [Python dividend documentation](https://pypi.org/project/norgatedata/), [current EULA](https://norgatedata.com/subscribe/eula.php). No private identities, dates or amounts were sent in web queries. Detailed data remain local and ignored; local report aggregate publication/retention still requires rights review.

## Trial-history limitation and terminal scope correction

The extended request does **not** mean 2023 history was delivered. Aggregate local verification found only **217 SPY bars preceding study start** and 539 securities with any prices before the old January-2025 request. Norgate's FAQ explicitly limits trial history to two years and says additional trial history is unavailable. The 270-bar requirement therefore prevents any signal in the first 52 study sessions under this acquisition. The remaining **26,686** warmup-constrained member dates across **512** securities are not all IPOs; benchmark/provider-window truncation dominates early observations. This is a material **BLOCKED** full-window coverage gate, not something the structural validator's PASS clears. No effort to bypass the trial or seek new access was made.

Expanded extraction now observes 16 terminal price series and 15 with last-bar membership 1 across its broader range. This must not be conflated with the original 13 in the earlier requested range; pre-study terminal cases cannot create an empty-start study holding. The corrected frozen-feature screen identifies **2 candidates with a possible pre-terminal entry signal**. They require settlement review; no actual A/B/C positions or terminal NAV losses have been computed. Per-event identities, exact dates and signal dates stay in private v2 JSON. The final audit is v2, not provisional v1.

Added restricted files requiring inventory/expiry handling: batch4a7_warmup_v1.sqlite, batch4a7_clearance_v1.json (superseded), batch4a7_clearance_v2.json, batch4a7_validation_v1.json and batch4a7_validation_v2.json. Script hashes and acquisition metadata are in their private records. Two independent acquisitions remain intact, not overwritten.

Final terminal time-scope check: among the 15 expanded-extract last-member terminal cases, **7 terminate before study start and 8 within the study window**. This is a calendar classification, not a finding of actual held positions. The two possible-entry candidates come from truncated in-study feature evaluations; all actual holdings remain unverified. The original 13-case count must retain its earlier extraction-range label.
