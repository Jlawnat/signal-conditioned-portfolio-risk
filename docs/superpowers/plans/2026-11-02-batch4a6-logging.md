# Batch 4A.6 Decision and Execution Logging Implementation Plan

**Goal:** Archive decision plans and subsequent simulated execution with auditable links, without changing V5-U economics.

**Architecture:** A versioned copy of the V5-U runner emits local JSONL through a pure logging module. The module calculates the common stop-gap measure, order identities, lifecycle and pair estimands. Synthetic tests exercise the module and a static runner integration check; the historical runner is not executed in this batch.

**Tech Stack:** Python standard library, pytest.

**Spec:** `docs/BATCH4A6_DECISION_EXECUTION_LOGGING_SPEC_DRAFT.md`.

## Global Constraints

- Frozen FMA and V4/V5-U outputs are read only.
- No full historical or Norgate PIT simulation, commit, push or external telemetry.
- The source runner rejects splits and has no partial fills.
- Preserve the executor's order and fill semantics.

## Review Focus

- S1 follows MPB exits and overlay, before buys.
- T-close decision records must be flushed before the next session's bar is read.
- Missing opening prices or invalid NAV yield missing exposure, never zero.
- Opening cash and position-cap rejection must terminate an order lifecycle.
- A's 4% comparison is a common reference, not an own overlay failure.

---

### Task 1: Logging primitives and schema

**Files:** Create `src/portfolio/decision_execution_log_v1.py`; test in `tests/test_decision_execution_log_v1.py`.

- [x] Implement deterministic IDs, risk snapshots, projected positions, lifecycle state recording and pair estimands.
- [x] Test no-order, sells, buys, mixed plans, missing risk and stable identities.

### Task 2: Versioned runner integration

**Files:** Create `scripts/run_mpb_lifecycle_v5u_logged_v1.py` from the V5-U source; document in `docs/BATCH4A6_LOGGING_SCHEMA_V1.md`.

- [x] Instrument S0 through S5 and proposed/accepted/rejected orders at the actual stage boundaries.
- [x] Write the decision file at T close before next-loop opening data access; use separate versioned output paths.
- [x] Reconcile accepted orders with fills and opening rejections.

### Task 3: Synthetic verification and audit

**Files:** Create `tests/test_batch4a6_synthetic.py`, `docs/BATCH4A6_IMPLEMENTATION_AUDIT.md`.

- [x] Exercise spec scenarios, forward-bar mutation and logging-on/off economic output equality with synthetic inputs.
- [x] Record exact gate results, unsupported cases and external replay blockers.
