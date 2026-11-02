# Batch 3 corporate actions and risk timing

No historical result was changed. The V5-U comparison and summaries reconcile 31/43/44 provider-only provisional events for A/B/C and endpoint unpaid receivables of $7,164.497493/$8,396.794868/$7,525.239390. The local manifest has 1,929 provider dividend entries and 23 splits bundle-wide; only two cash events are curated with separate declarations and payment dates (USB and CAT). Provider factor agreement is **not** independent confirmation of cash payment. The runner rejects splits or other unsupported actions affecting a held or pending symbol; this does not validate every bundle action.

Replaying stored fills up to the two curated ex-dates gives the following ex-date entitlements, before that morning's fills. The payments are registered with pay dates; the ex-date share arithmetic is directly checkable. Provisional totals use the stored unsettled receivable, which is not spendable cash.

| Policy | USB curated ($) | CAT curated ($) | Curated total ($) | Provisional accrued and unpaid at endpoint ($) | Combined accrual ($) |
|---|---:|---:|---:|---:|---:|
| A | 391.04 | 13.59 | 404.63 | 7,164.497493 | 7,569.127493 |
| B | 391.04 | 99.66 | 490.70 | 8,396.794868 | 8,887.494868 |
| C | 391.04 | 98.15 | 489.19 | 7,525.239390 | 8,014.429390 |

The A combined accrual rounds to $7,569.13 in the existing A P&L forensics. These totals classify simulated accruals, not independently verified receipt of every dollar. Removing only endpoint provisional receivables from reported NAV yields A $947,433.93, B $917,507.59, C $934,429.36; the arithmetic ranking remains A > C > B. This is **not a full-path counterfactual**: earlier receivables affect denominators used in sizing and budgets, while a different payment calendar could affect cash and later trades. Event-level official declarations, entitlement checks and payment dates for 31/43/44 provider-only events are missing, so a defensible full-path bound cannot be established without a separately versioned sensitivity replay. Ex-date stop reductions use dividend amounts and remain a model assumption.

`scripts/paper/batch3_risk_timing.py` independently replays immutable fills and marks for the three largest stored own-budget breach dates per policy. It computes: (1) T-close observed risk before new planning; (2) T-close **hypothetical** risk after the actual following-session sell quantities, held at T prices and NAV; (3) T+1 open risk after actual simulated fills and opening marks; (4) T+1 end-of-day observed risk. Step 2 is an ex-post proxy for planned sells, not a retained order-book snapshot; it includes all next-open sells, whether MPB or overlay. The sample output is `paper/tables/v2/risk_timing_sample.json`.

| Policy; T close | T budget % | Before plan % | Hypothetical after sells % | T+1 post-fill open % | T+1 close % |
|---|---:|---:|---:|---:|---:|
| A; 2025-10-23 | 4.0000 | 5.2645 | 5.2645 | 5.5785 | 5.2803 |
| B; 2025-10-23 | 4.0000 | 5.3795 | 3.9972 | 4.3026 | 4.1652 |
| C; 2025-10-23 | 4.3272 | 5.6817 | 4.3237 | 4.7080 | 4.5116 |
| B; 2026-06-04 | 4.0000 | 4.9515 | 3.9988 | 4.0100 | 4.0041 |
| C; 2026-01-05 | 5.0000 | 6.2915 | 4.9987 | 4.5784 | 4.7926 |

These selected cases demonstrate price-gap and later-mark effects after a T-close integer-share target. They do not apportion all 81/78 B/C breach days by cause. The T+1 own C budget can change with its new closing volatility; the T budget in the table is only the preceding decision target. For A's three sampled largest breaches there were no next-open sells, consistent with no incumbent overlay. B/C's selected sells carry `risk_budget_overlay` reasons. No exact per-day decomposition of integer rounding, target updates, sector interactions, pending sells and subsequent portfolio changes exists in the stored artifacts. The full 282-session risk audit remains a close observation: own-budget breach days A/B/C = 130/81/78; common 4% days = 130/81/165; sector 24% days = 8/9/24. C's common 4% excess is not automatically an own-budget violation. Neither B nor C fully enforces its budget at realized marks.
