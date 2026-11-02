# Capital deployment and efficiency: Batch 3 definition

**Implemented observation.** The daily invested fraction is `(NAV − cash − dividend receivable)/NAV`; mean V5-U fractions are A 33.2569%, B 34.5098%, C 37.6113%. Cash fractions are 66.4302%, 65.1031%, 62.0110%. Receivables explain why these pairs do not sum exactly to 100%. A larger invested fraction is a **deployment level**, not evidence of efficient allocation.

**Conceptual distinction.** Deployment efficiency would require a justified relation among available qualified opportunities, capital and risk capacity used, net returns, and implementation frictions. The current outputs reveal capital use and modeled costs, but do not identify an optimal allocation or a clean counterfactual for trades forgone under each policy. Policies change future holdings and candidate eligibility. The 1,229 candidate events describe the stored signal pool, not necessarily executable opportunities after holdings, sector, cash and volume checks.

| Descriptive diagnostic | Observability | Interpretation |
|---|---|---|
| Average invested capital/NAV and cash/NAV | Direct from 282 daily rows | Deployment level and idle cash, conditional on receivables. |
| Own-budget utilization `R_t/b_t` and unused capacity `max(0,b_t−R_t)` | Reconstructable from fills, stops and prices | Capacity of a **stop-gap proxy**, not deployable dollars or VaR. Above-budget days must remain visible. |
| Qualified candidates per day | Precomputed CSV | Signal availability before portfolio constraints; no full rejection log. |
| Fill count and modeled cost | Trade and comparison files | Friction and activity; fill count alone is not turnover dollars. |
| Net return relative to average invested capital | Mathematically possible | Post-hoc exploratory ratio with unstable denominator and path dependence; unsuitable as proof of skill or optimality. |

**V2 decision.** Use “capital deployment” for observed investment exposure. Retain “deployment efficiency” only as a motivation and unresolved research question. No new efficiency estimand is promoted to the post-hoc primary outcome hierarchy. A future confirmatory study should predefine opportunity eligibility, turnover notional, attributable net P&L and a matched opportunity set before estimating any efficiency claim. Researcher approval is required for any new metric or revised hierarchy.
