# Batch 2 dividend, corporate-action and constraint-timing audit

Review date: 2026-11-02. No historical simulation or audit output was edited.

## Dividend and action classes

The curated `configs/verified_cash_dividends.json` contains independently registered events; `tests/test_corporate_actions.py` checks one USB event's amount, ex-date/pay-date accounting and factor arithmetic. The local provider manifest contains reconciled adjustment-factor events, but provider agreement is not independent verification of payment. `audit/corporate_actions_inventory_summary.json` reports 1,952 provider events in the bundle: 1,929 dividends and 23 splits; status counts are 2 curated registered, 1,927 provider-only unverified and 23 split unmodeled. These bundle totals are not counts of affected holdings.

V5-U A/B/C used 31/43/44 provisional provider-only events. Their endpoint unpaid receivables were $7,164.497493/$8,396.794868/$7,525.239390, respectively, and those values are included in reported NAV. The runner's `UNSETTLED_RECEIVABLE_NO_CASH_CREDIT` policy prevents crediting them as spendable cash. Ex-date stops are adjusted by assumed dividend amounts. Neither a full verified payment calendar nor an independent entitlement audit for all provider-only events is available.

**Bounded arithmetic sensitivity, holding trades and all other marks fixed:** if only the *endpoint unpaid provisional receivable* is removed, A/B/C NAV becomes $947,433.93/$917,507.59/$934,429.36. This is a conditional component subtraction, not a lower confidence bound on an alternative simulation: uncertain earlier accruals may have changed NAV, budgets, trades and subsequent positions. It does show that this one endpoint component alone does not reverse A > C > B. A defensible full-path dividend bound requires event-level payment and entitlement evidence, plus a versioned replay if the economic accounting changes.

## Constraint timing

The V5-U independent constraint audit reconstructs end-of-day holdings, raw-close risk and sector values for 282 sessions. A/B/C were above own budget on 130/81/78 days, above fixed 4% on 130/81/165, and above 24% sector weight on 8/9/24. Maximum own-budget excess was 1.3834/1.3795/1.3544 percentage points. These are observed close values. C's variable budget reaches 5%, so its fixed-4% count cannot be treated as a violation of C's own target.

The planner calculates risk before new orders at T close, schedules MPB exits, and computes B/C additional trims from the remaining position risk. The extra sells become pending orders. They can fill only at T+1 open, at a price different from T close. The current full-history artifact does not retain the risk measure at each of the four requested states—before planned orders, after planned reductions, post-fill open, and close. `audit/p3_constraint_timing_summary.json` examines 30 V4 sessions, 15 exception days; it cannot establish V5-U timing attribution. The V5-U end-of-day breach count therefore establishes residual exposure, while the mechanism of each breach remains **PARTIAL / NOT_TESTED**.

The position and holding limits show zero observed days above 10% and 14 holdings, respectively; the sector reference has residual breaches. No statement that B or C fully enforced its budget is supported. Publication language should say "planned T-close reduction" until an actual fill is confirmed. A bounded future audit should select breach dates and reconstruct the four states from immutable input/output files, without changing the original paths.
