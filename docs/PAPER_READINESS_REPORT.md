# Paper readiness report

Review date: 2026-11-02. Phase: evidence consolidation and verification, ready for a qualified Methods/Results draft; final causal or performance conclusions are not ready. This review did not run a new 282-session simulation or alter historical outputs.

## 1. Results safe to describe now

The **V5-U transaction-cap-neutral historical simulation** covers 282 sessions, 2025-09-18–2026-10-30. The report's twelve source hashes matched existing summaries, daily files, trades and accounting audits. Recomputed terminal NAV, return and maximum drawdown matched all three reported rows. The fixed $1 million starting NAV and descriptive outcomes are:

| Policy | Ending NAV | Return | Max drawdown | Mean invested | End-of-day days above own budget | Execution cost |
|---|---:|---:|---:|---:|---:|---:|
| A | $954,598.43 | −4.5402% | 6.0091% | 33.2569% | 130 | $9,491.45 |
| B | $925,904.38 | −7.4096% | 9.0257% | 34.5098% | 81 | $12,675.68 |
| C | $941,954.60 | −5.8045% | 8.2399% | 37.6113% | 78 | $13,336.02 |

Sources: `audit/p3_abc_v5u_282d_comparison.json`, `audit/p3_abc_v5u_282_constraints.json`. B and C showed fewer own-budget breach days than A in this simulation, while their realized drawdowns and terminal returns were worse. C exceeded fixed 4% on 165 days, consistent with a budget that may rise to 5%; own-budget and fixed-threshold counts answer different questions. Sector weight exceeded 24% on 8/9/24 days for A/B/C. These are end-of-day observations, not proof of pretrade noncompliance.

Accounting replay passed for all 282 sessions and 313/464/478 fills in A/B/C. The stored differential matched 17/17 synthetic frozen-reference exit cases; reference source/config hashes matched. These are bounded software checks.

## 2. Results requiring qualifications

The V5-U figures include 31/43/44 provisional provider-only dividend events and $7,164.50/$8,396.79/$7,525.24 in unpaid provisional receivables at the endpoint. Those amounts are inside reported NAV; they are not independently verified cash receipts. This is material for return ranking and should be visible in every performance table. The provider event inventory is broad; it does not imply every unverified event affected held positions.

V4 is a distinct **contest-capped planning** scenario: B NAV $940,072.59, return −5.9927%, drawdown 6.5576%; C NAV $958,904.64, return −4.1095%, drawdown 5.1563%. Its B/C paths cannot be substituted for V5-U. The nominal planning threshold is 360, yet V4 B/C have 370/373 fills because the check is not a strict global executed-fill cap. Describe it as a planning rule, not a guaranteed realized limit.

The 30-session positive B/C pilot, cash-interest shadow scenarios and supplementary StockTrak reconciliation cannot establish a full-period improvement. Cash-interest shadows are illustrative sums, not integrated portfolio NAVs. Historical data and policy paths have already been inspected. No inference should label this period out-of-sample, prove statistical significance, or attribute path differences solely to the overlay.

## 3. Analyses required before final conclusions

1. Certify or explicitly bound reference signal and order-planning fidelity. Current signal differential covers all reported positives, sampled negatives and seven complete dates; full reference signal/order parity remains untested. Compare selected, ranked and rejected orders, quantities, constraints and transaction-cap behavior against frozen FMA on a predeclared sample. Keep the original source untouched.
2. Resolve or bound the NAV effect of provisional dividends and corporate-action assumptions, especially unpaid receivables and ex-date stop adjustments. Use local evidence; disclose any remaining unresolved amounts. Do not silently change prior outputs.
3. Audit V5-U constraint timing at planning, post-open execution and close on breach dates; identify drift, fill price, sizing or planning causes. Current 282-session constraint replay is observational. The 30-session timing diagnostic is insufficient for full-span compliance language.
4. Finalize the estimands and presentation hierarchy in `docs/RESEARCH_PROTOCOL_V1.md`, then produce a transparent paired descriptive analysis of deployment, breaches, cost and NAV with uncertainty treatment appropriate to an inspected sample. A causal claim needs additional identification and cannot be inferred from these paths alone.
5. Record a reproducible local manifest with hashes, environment versions and source lineage. The current raw data and signal candidate files are outside this repository.

## 4. Optional work that should not delay writing

Independent future-period or point-in-time-universe data could improve external validity but is not a prerequisite for a clearly labeled exploratory paper. Integrated cash-interest scenarios, broader cost sensitivities, and auxiliary allocation are extensions, not repairs to the present A/B/C comparison. Literature and citation verification must occur during manuscript writing; none is inferred here.

## Integrity audit verdict

| Check | Classification | Reason |
|---|---|---|
| Report-to-output figures and hashes | PASS | All twelve V5-U file hashes; row counts, dates, NAV, return, drawdown recomputed. |
| Independent cash/NAV/T+1 replay | PASS | Three 282-session reports, accounting scope only. |
| Frozen FMA source identity | PASS | Two source hashes matched snapshot. |
| Exit decision fidelity | PARTIAL | 17/17 stored synthetic cases; user reports 408/408 sampled formula cases, but its artifact was not located here; no order parity. |
| Full historical signal and order fidelity | PARTIAL / NOT_TESTED | Signal differential is sampled on negatives; order generation has no full comparison. |
| Execution cost definition | PASS for code inspection | $10/fill plus 5 bps adverse opening slippage; realism beyond model untested. |
| Constraint definition and realized compliance | PARTIAL | Stop-based risk formula inspected; end-of-day breaches observed; full timing and pretrade causes unresolved. |
| Corporate actions and dividends | PARTIAL | Curated checks pass; provider-only claims and stop assumptions remain provisional. |
| Point-in-time membership / independent holdout | MISSING | Current constituents and previously inspected period. |

No direct mismatch was found in the checks executed. No finding of economic superiority or MPB-only StockTrak performance follows from this audit.
