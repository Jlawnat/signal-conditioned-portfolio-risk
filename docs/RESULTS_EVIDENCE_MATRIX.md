# Results evidence matrix

Use this matrix when drafting tables or claims. `VERIFIED` means a bounded check supports the stated descriptive fact; `PROVISIONAL` means the number is reproducible under assumptions but its economic interpretation remains qualified; `MISSING` means the required evidence is absent.

| Draftable statement | Source / validation | State | Required wording or boundary |
|---|---|---|---|
| V5-U A/B/C ending NAV $954,598.43 / $925,904.38 / $941,954.60 and returns −4.5402% / −7.4096% / −5.8045% | `audit/p3_abc_v5u_282d_comparison.json`; twelve hashes and recomputation from daily NAV | VERIFIED numerical; PROVISIONAL economic | Hypothetical, transaction-cap-neutral, inspected historical sample; includes provisional receivables. |
| V5-U maximum drawdowns 6.0091% / 9.0257% / 8.2399% | Same daily NAV recomputation | VERIFIED numerical | NAV path drawdown, separate from mark-to-stop budget risk. |
| V5-U mean deployment 33.2569% / 34.5098% / 37.6113% | Comparison report and constraint audit | VERIFIED descriptive | Means over 282 daily observations, not capital efficiency proof. |
| V5-U own-budget breach days 130 / 81 / 78 | `audit/p3_abc_v5u_282_constraints.json` | VERIFIED observational | End-of-day mark-to-stop; T+1 execution and drift can breach targets. |
| V5-U fixed 4% breach days 130 / 81 / 165 | Same constraint audit | VERIFIED observational | C's own budget is variable, up to 5%. |
| V5-U sector >24% days 8 / 9 / 24 | Same constraint audit | VERIFIED observational | End-of-day, not pretrade attribution. |
| V5-U fill counts 313 / 464 / 478 and cost $9,491.45 / $12,675.68 / $13,336.02 | Per-policy trade files, summaries, comparison | VERIFIED within modeled execution | $10/fill and 5 bps adverse slippage; no market impact. |
| V4 B/C NAV $940,072.59 / $958,904.64 | `audit/p3_abc_282d_comparison.json` | VERIFIED prior artifact; separate scenario | Contest-capped *planning* threshold; never combine with V5-U rows. |
| V5-U provisional event counts 31 / 43 / 44, endpoint receivables $7,164.50 / $8,396.79 / $7,525.24 | V5-U summaries and comparison | PROVISIONAL | Provider-only entitlement/pay-date assumptions; included in NAV. |
| Frozen exit decision matches | `audit/mpb_exit_differential.json`, 17/17; source hashes checked | VERIFIED for synthetic decision cases | Does not cover full signal features, ranking, order generation or historical behavior. |
| 408/408 sampled exit-formula parity | User-provided verified context; artifact not located in inspected directories | PROVISIONAL for this package | Cite only after locating immutable audit artifact and sample definition. |
| Historical signal match | `~/FMA_Independent_Research/audit/signal_differential_summary.json`: 4,874 checks | VERIFIED for checked cases; PARTIAL overall | All reported positives, sampled negatives, seven complete sessions. |
| Full reference signal/order parity | No full comparison found | MISSING | Cannot call the research planner a certified reproduction of FMA. |
| Cash-interest adjusted performance | `audit/p3_cash_interest_scenarios.json` | PROVISIONAL illustrative | Shadow arithmetic only; not integrated NAV or original results. |
| MPB-only StockTrak returns | Supplementary account reconciliation, no transaction-level evidence inspected | MISSING | No MPB-only performance claim. |
| Statistical significance, causal benefit, out-of-sample alpha | No valid current basis | MISSING | Do not claim. |
