# Batch 4A.6 — Decision-to-Execution Logging Specification

**Project:** Signal-Conditioned Portfolio Risk  
**Status:** Draft — Researcher Review Required  
**Purpose:** Publication-grade decision and execution evidence for a future point-in-time portfolio experiment  
**Scope:** Logging instrumentation, synthetic validation and reproducibility only. No new historical strategy replay.

## 1. Research Objective

Develop an auditable logging system that preserves the information available when portfolio decisions were made and records the corresponding simulated execution outcomes.

The system must support measurement of the gap between planned stop-gap exposure and observed post-execution exposure.

Existing V4 and V5-U outputs must remain immutable. The previously inspected 282-session results remain exploratory.

## 2. Required Event Sequence

Every policy and trading session must preserve the following states in chronological order:

| State | Event | Required record |
|---|---|---|
| S0 | T close, before decisions | Existing positions, stops, cash, receivables, NAV and risk |
| S1 | T close, after risk-overlay stage | Positions implied by the overlay decision and intermediate risk |
| S2 | T close, after all final planned orders | Complete planned positions and final planned risk |
| S3 | T+1 open, before fills | Opening marks, corporate-action-adjusted positions, stops and pre-fill risk |
| S4 | T+1 open, after all fills | Actual simulated positions, costs, cash, NAV and post-fill risk |
| S5 | T+1 close | Closing positions, NAV and marked exposure |

S1 must follow the executor's actual stage ordering. Do not falsely identify it as an overlay-only state if other trades have already been incorporated.

S2 is the primary decision-time snapshot. It must include all accepted planned sells and buys, not only overlay reductions.

Save the final decision record before any T+1 market information is consumed by the decision logic.

The event timestamps are logical simulation timestamps, not assertions that a real broker received orders at those times.

## 3. Required Identifiers and Provenance

Each event should contain:

- `run_id`
- `policy_id`
- `decision_id`
- `order_id` where applicable
- `decision_date`
- `execution_date` where known
- `event_sequence`
- `simulation_phase`
- `simulation_timezone`
- `information_cutoff`
- `record_origin` (`decision_time`, `execution_time`, `reconstructed`)
- `strategy_config_hash`
- `data_manifest_hash`

Use deterministic, collision-resistant identifiers that allow each order to be traced back to its decision and policy.

The initial logging implementation must preserve records locally and avoid external telemetry or API uploads.

## 4. Planned Order Records

For each proposed and accepted order, record:

- Symbol and stable security identifier, where available
- Action (`BUY` / `SELL`)
- Requested shares
- Accepted planned shares
- Rejected planned shares, where applicable
- Reason and strategy component
- MPB exit quantity, overlay reduction quantity and final netted quantity
- Decision-time reference price
- Decision-time stop and adjustment factor
- Estimated transaction costs
- Cash availability and risk-limit checks
- Final planned order state
- Links to subsequent simulated execution records

Do not infer planned orders from later fills.

Preserve proposed, rejected and accepted orders separately.

If multiple reasons combine into one execution order, preserve the individual components and the final combined quantity.

## 5. Exposure Snapshot Records

At S0, S1, S2, S3, S4 and S5, retain:

- `nav`
- `cash`
- `dividend_receivable`
- `holdings_count`
- Position quantities and relevant adjusted stops
- Valuation price source and time
- `risk_numerator`
- `risk_denominator`
- `marked_stop_gap_exposure`
- `budget_fraction`
- `reference_budget_fraction`
- `budget_excess_fraction`
- `calculation_status`
- `missing_input_reasons`

The exposure calculation must use the research-approved stop-gap definition consistently:

R = sum over positions of shares × [max(0, marked price − adjusted stop) + 0.01 × marked price], divided by NAV.

The portfolio planner's existing `projected_risk` output must not automatically be treated as this measure if its calculations differ.

For S2, use T-close prices, the final accepted planned quantities and the approved decision-time NAV convention.

The proposed convention is T-close NAV as the exposure denominator, with projected execution costs reported separately. Confirm this convention before freezing the research protocol.

For S4, use the actual simulated post-fill NAV after execution costs and the actual post-fill position state.

If an exposure cannot be calculated reliably, record it as missing with a reason. Never silently substitute zero.

## 6. Order Lifecycle

Represent every order's transition through states such as:

`PROPOSED`, `ACCEPTED`, `QUEUED`, `REJECTED`, `PARTIALLY_FILLED`, `FILLED`, `CANCELLED`, or `EXPIRED`.

Each state change must have a logical event sequence and an explicit reason when relevant.

A decision can produce zero orders; its snapshot must still exist.

No order may disappear from the lifecycle without a recorded terminal or carried-forward state.

The existing executor's actual fill assumptions must remain unchanged by instrumentation.

## 7. Mechanism Estimands

For each valid adjacent trading-session pair:

**Execution implementation gap**

G_T = R(T+1, open, post-fill) − R(T, final plan)

**Positive implementation gap**

G_T_positive = max(G_T, 0)

**Planned-compliant-to-post-fill-exceedance indicator**

I_T = 1 when both:

- R(T, final plan) is no greater than b_T + epsilon; and
- R(T+1, open, post-fill) exceeds b_T + epsilon.

Otherwise, for a valid observation, I_T = 0.

Here b_T is the budget known at T decision time.

For Policy C, do not substitute a newly calculated T+1 closing budget.

Policy A does not have the same incumbent-holdings overlay requirement as B/C. Any evaluation against 4% for A must be labelled a common reference comparison, not A's own mandatory budget-compliance failure.

The numerical tolerance `epsilon` must be chosen and documented before the main experiment.

Report gaps separately for all valid adjacent sessions, sessions with orders, and sessions with overlay interventions. These populations must not be chosen after observing new results.

An implementation gap is not automatically execution slippage, a system failure or a causal effect of the overlay.

## 8. Observation Coverage

The historical reference study contains 282 trading sessions and therefore at most 281 adjacent-session pairs per policy.

For future studies:

- Include no-order sessions in the complete observation calendar.
- Preserve rejected, partially filled and cancelled orders.
- Do not score the final study session as zero when T+1 data are unavailable.
- Report missing observations, exclusions and policy-specific denominator counts.
- Distinguish opening exceedance events from later closing exceedance persistence.
- Keep exploratory historical results separate from later confirmation results.

## 9. Validation Test Suite

The implementation must pass synthetic tests for:

1. No-order sessions.
2. Planned sells only.
3. Planned buys only.
4. Combined MPB and overlay sells.
5. Combined buy/sell planning.
6. Cash-based order rejection.
7. Partial fill or cancellation, if the executor supports it; otherwise explicitly document the unsupported case.
8. Overnight gap-up and gap-down.
9. Different estimated versus realized trading costs.
10. Dividend and split events using synthetic inputs.
11. A dynamic Policy C budget change between decision and later closing observations.
12. Missing next-session prices and invalid risk inputs.
13. Deterministic replay and stable identifiers.
14. Cross-file accounting and order reconciliation.
15. Forward-information isolation: changing future bars must not change the archived T decision-time plan.

### Non-interference requirement

With logging disabled and enabled on identical synthetic inputs, compare:

- Trading decisions
- Planned order quantities
- Simulated fills
- Cash
- NAV
- Holdings
- Costs
- Risk-budget decisions

All economically relevant outputs must remain identical under documented numeric tolerances.

Use synthetic fixtures and separate output paths.

Do not require Norgate raw data for this test suite.

## 10. Security and Licensing

Do not commit proprietary Norgate prices, membership snapshots, security identifiers or source-derived raw observations.

If future simulations use Norgate data, write full research event records to restricted local storage until retention and publication rights have been established.

Only synthetic fixtures, code, schemas and approved aggregate reports may be candidates for public version control.

No API calls, cloud uploads, Git pushes or subscription actions are part of this batch.

## 11. Versioning and Implementation Constraints

Implement logging in a separate, versioned research execution path or through isolated instrumentation.

Do not rewrite the frozen FMA reference implementation.

Do not overwrite historical V4/V5-U runs or previous research manifests.

Prefer narrow, testable changes over restructuring the whole simulator.

Any intentional change in strategy behavior requires separate approval and cannot be hidden inside a logging change.

## 12. Required Deliverables

- A documented event and order schema
- A decision-time snapshot writer
- An execution-time snapshot writer
- Deterministic order linkage and reconciliation
- A standalone synthetic validation suite
- An audit report with exact test results
- A non-interference comparison
- A separate versioned runner or instrumentation mechanism
- A clear readiness decision

## 13. Acceptance Gates

| Gate | Required result |
|---|---|
| LOG_SCHEMA_READY | All required fields and event states documented |
| DECISION_SNAPSHOT_READY | Complete final planned positions and exposure recorded before T+1 information |
| EXECUTION_SNAPSHOT_READY | Post-fill positions, NAV and exposure recorded |
| ORDER_TRACEABILITY_READY | Planned and executed quantities reconciled |
| RISK_DEFINITION_READY | Same approved exposure formula applied at decision and execution stages |
| NO_LOOKAHEAD_READY | Forward-information isolation test passed |
| NON_INTERFERENCE_READY | Instrumentation demonstrably preserves economic outputs |
| SYNTHETIC_TESTS_READY | All applicable scenarios passed or explicitly reported unsupported |
| READY_FOR_PIT_MECHANISM_REPLAY | All preceding gates passed and external data gates separately cleared |

The final gate must remain BLOCKED if material Batch 4A market data, corporate-action, historical-sector or authorization issues are unresolved.

## 14. Research Integrity

Do not reclassify the existing reconstructed nine-case timing sample as decision-time archived evidence.

Do not present synthetic validation as empirical confirmation.

Do not claim a causal decomposition without a prespecified counterfactual calculation.

Do not begin a full historical PIT replay in Batch 4A.6.

**The purpose of Batch 4A.6 is to make subsequent empirical results auditable, not to generate favorable new results.**