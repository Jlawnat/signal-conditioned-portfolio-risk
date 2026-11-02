# Draft V1 adversarial review

This is an editorial review companion, not part of the manuscript. It follows the research-paper-writing skill's five review dimensions.

| Dimension | Status | Evidence or revision needed |
|---|---|---|
| Contribution | PARTIAL | The defensible contribution is a transparent case comparison of planned risk, constraints, deployment and realized outcomes. No claim of a new optimal rule or general performance gain is made. A sharper literature gap needs more targeted source work. |
| Writing clarity | PASS for Draft V1 | A/B/C, V4/V5-U, T-close/T+1 and stop-gap risk are defined before the result interpretation; figures and tables are linked. |
| Experimental strength | PARTIAL | A/B/C share a historical window but policy paths differ. B/C do not improve NAV or drawdown in V5-U; no independent holdout or confirmatory test exists. |
| Evaluation completeness | PARTIAL | NAV, drawdown, deployment, costs and constraint observations are present. Full signal/order parity, V5-U breach timing, and dividend-path sensitivity remain. |
| Method soundness | PARTIAL | Frozen feature source and managed exit core have bounded checks. Candidate/order integration and hypothetical fills remain limiting assumptions. |

## Claim–evidence map

| Major claim | Evidence | Status |
|---|---|---|
| B/C have fewer days above own budget in V5-U | Reconstructed risk paths agree with `audit/p3_abc_v5u_282_constraints.json` | Supported descriptively |
| B/C have worse terminal NAV and maximum drawdown than A in V5-U | Source-hash-verified daily files and comparison report | Supported numerically; dividend-conditioned |
| C exceeds common 4% more often than A/B | Same constraint audit and C budget formula | Supported descriptively |
| The overlay causes the worse NAV | No causal isolation; different future holdings | Not claimed |
| MPB has reliable predictive edge | Selected entry diagnostics, inspected period | Not claimed |
| Independent runner fully reproduces FMA orders | No full order differential | Not claimed |

The abstract and introduction were checked against this map. Submission review should revisit every PARTIAL item after the remaining audits and target-journal choice.
