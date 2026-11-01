# Research Status

Snapshot: 2026-11-01

## Completed preliminary checks

- 282 evaluable historical signal dates.
- 1,229 reported historical MPB signal events.
- 4,874 independently checked stock-date observations.
- Preliminary empty-portfolio capacity bounds.
- 1,229 T+1 signal observations classified.
- 13 adjustment changes internally reconciled.
- 21 signals right-censored at the sample boundary.
- Single-asset accounting and historical-fill tests passed.
- Five-session CHRW round-trip accounting test passed.

## Current engineering phase

Phase 3: Multi-Period Portfolio Research System.

### Multi-asset pilot

- 12 sessions requested
- 8 sessions completed
- 13 simulated buy fills
- Daily accounting identity: PASS
- Status: BLOCKED
- Reason: USB adjustment-factor change on 2025-09-30

This is an expected safety stop, not a completed backtest.

## Work remaining

1. Complete literature-gap verification.
2. Finalize data and experimental protocols.
3. Implement corporate-action-aware portfolio accounting.
4. Implement original strategy exit lifecycle and
   independent auxiliary allocation.
5. Run and verify full historical portfolio simulations.
6. Conduct statistical inference, robustness checks,
   manuscript preparation and final reproducibility audit.

## Integrity rules

Do not report synthetic tests as historical strategy returns.
Do not modify the original frozen competition engine.
Do not use future prices for historical trading decisions.
Do not publish private account records or licensed raw data.
