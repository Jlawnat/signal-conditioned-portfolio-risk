# Batch 4A.6 implementation audit — 2026-11-02

## Execution-order findings before coding

Inspected `scripts/run_mpb_lifecycle_v5u.py` and the read-only timing findings in `docs/BATCH3_CORPORATE_ACTION_AND_RISK_TIMING.md`. No separately named Batch 4A.5 mechanism-feasibility file was present in this workspace. The existing nine-case sample is a post-hoc reconstruction from fills, not a decision-time archive. The executor's actual order is: payment settlement → ex-date action adjustment → opening mark → whole-order sells then buys → post-fill mark → closing mark → T-close budget → MPB exits → B/C overlay merged into exits → buys. Accordingly S1 contains MPB exits and overlay reductions; S2 adds final buys. Neither S1 nor S2 may be inferred from fills. The executor does not support partial fills or splits affecting holdings/pending buys. No investment rule was changed to add either capability.

## Files created and modified

Created `src/portfolio/decision_execution_log_v1.py` (risk, IDs, append-only local journal, lifecycle and reconciliation), `scripts/run_mpb_lifecycle_v5u_logged_v1.py` (isolated V5-U copy with S0–S5 hooks and private versioned output), `tests/test_batch4a6_synthetic.py` (standalone synthetic suite, including execution-loop differential), `docs/BATCH4A6_LOGGING_SCHEMA_V1.md` (schema and conventions), `docs/BATCH4A6_IMPLEMENTATION_AUDIT.md` (this report), and `docs/superpowers/plans/2026-11-02-batch4a6-logging.md` (implementation map). No pre-existing tracked file was modified by this batch. The pre-existing working-tree changes to `configs/verified_cash_dividends.json`, the draft spec, other plan, and paper table JSON files were left untouched. Frozen FMA source, V4/V5-U outputs and manuscript files were not written.

## Verification and limitations

`pytest -q tests/test_batch4a6_synthetic.py`: **PASS, 7 passed**. `pytest -q tests`: **PASS, 25 passed, 1 skipped**. `python3 -m py_compile scripts/run_mpb_lifecycle_v5u_logged_v1.py src/portfolio/decision_execution_log_v1.py`: **PASS**. The test compiles and executes the actual original and logged **day loops** against identical synthetic data. It compares economic state with logging disabled and enabled for no-order, sells-only, buys-only, mixed buy/sell, a combined MPB/overlay sell, an opening cash rejection and a dividend. It mutates a future opening bar and verifies byte-equivalent S2 records and unchanged decision quantities. It verifies accepted order IDs and quantities against fills, and checks missing-price and split abort records. Pure-function tests cover gap up/down, planned versus realized cost denominators, a later Policy C budget change, invalid risk inputs and deterministic IDs. The split arithmetic fixture checks only snapshot representation; the actual runner correctly blocks a synthetic held split. No partial-fill test is applicable because the executor has no such fill path.

The synthetic loop executes extracted runner code with synthetic helper functions and panels; it does not import the frozen FMA reference, validate real candidate inputs or run the full script. No historical, Norgate PIT, or 282-session replay was performed. The T-close NAV convention is implemented as proposed and still requires researcher confirmation before protocol freeze. `epsilon = 1e-9` is fixed for this version. A future licensed replay must use restricted local storage and pass the separate Batch 4A data gates.

## Acceptance gates

| Gate | Result | Evidence or blocker |
|---|---|---|
| LOG_SCHEMA_READY | **PASS** | Schema v1 documents required common fields, S0–S5, order states, provenance, missing values and private paths. |
| DECISION_SNAPSHOT_READY | **PASS** | Synthetic S2 captures accepted sells and buys, final positions, T-close NAV exposure and costs before next-open data access; no-order S2 exists. |
| EXECUTION_SNAPSHOT_READY | **PASS** | Synthetic S3/S4 capture action-adjusted state, opening marks, actual fills, post-cost NAV and exposure; missing next-open input is explicit. |
| ORDER_TRACEABILITY_READY | **PASS** | Stable IDs join proposal, acceptance, queue, fill/rejection, S2 and independent `reconciliation.json`; synthetic reconciliation passes. |
| RISK_DEFINITION_READY | **PASS** | Identical 1% stop-gap formula is used in S2 and S4. T-close NAV is the explicit proposed S2 denominator; empirical protocol approval remains outstanding. |
| NO_LOOKAHEAD_READY | **PASS** | Mutating the synthetic T+1 opening price changes fills but leaves archived T S2 byte-identical. |
| NON_INTERFERENCE_READY | **PASS** | Actual day-loop differential matches decisions, planned quantities, fills, cash, NAV, holdings, costs and budget decisions on all tested synthetic scenarios. |
| SYNTHETIC_TESTS_READY | **PASS** | Seven tests cover all applicable requested cases. Partial fills and split execution are explicitly unsupported by the existing executor. |
| READY_FOR_PIT_MECHANISM_REPLAY | **BLOCKED** | Batch 4A membership, historical sector, corporate-action, terminal-price and authorization issues remain unresolved; denominator convention also awaits protocol approval. |

There are **no FAIL gates** in the bounded synthetic scope. PASS does not claim historical strategy fidelity, empirical mechanism confirmation, or approval to run licensed data.
