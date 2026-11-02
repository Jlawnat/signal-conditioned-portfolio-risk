# Signal-Conditioned Portfolio Risk Budgeting: Capital Deployment, Constraint Violations, and Risk–Return Trade-offs

*Manuscript Draft V1 · 2026-11-02 · exploratory historical simulation*

## Abstract

**Background.** Portfolio risk rules act on positions that depend on when qualifying signals arrive. A tighter planned-risk target can reduce measured exposure while changing future holdings, turnover and realized losses.

**Methods.** We compare a momentum–pullback–breakout baseline (A), a fixed 4% portfolio stop-gap risk overlay (B), and a volatility-conditioned 2%–5% overlay (C) over 282 historical U.S. equity sessions from 18 September 2025 to 30 October 2026. Decisions occur at the close and hypothetical fills at the next open. The main comparison uses a transaction-cap-neutral research scenario (V5-U), with the contest-capped planning regime (V4) shown separately. The outcome hierarchy was proposed after inspecting this history.

**Results.** In V5-U, end-of-day days above each policy's own budget were 130, 81 and 78 for A, B and C. Mean invested fractions were 33.2569%, 34.5098% and 37.6113%. Ending NAVs from $1 million were $954,598.43, $925,904.38 and $941,954.60, with maximum drawdowns of 6.0091%, 9.0257% and 8.2399%. B and C used 464 and 478 fills versus A's 313, increasing modeled execution cost. C exceeded the common fixed 4% risk reference on 165 days because its own budget could rise to 5%.

**Interpretation.** The overlays reduced own-budget exceedance counts in this implementation but did not improve the reported terminal NAV or maximum drawdown. These are conditional, descriptive results. The current-constituent universe, previously inspected period, hypothetical fills, provisional dividends and incomplete full signal/order parity limit inference. No claim of statistical significance, causal superiority or live strategy performance is made.

---

## 1. Introduction

Portfolio managers often limit exposure before an order is placed, yet the realized path of a portfolio depends on when eligible trades become available and how existing positions evolve. A position-level rule can leave capital idle during sparse signal periods; a portfolio-level rule can force reductions in incumbents without creating new opportunities. This paper studies that interaction within one frozen momentum–pullback–breakout (MPB) research strategy. The empirical object is the allocation and risk path produced by three specified policies, rather than a search for a more profitable entry rule.

Risk budgeting provides a language for assigning exposure across positions, but its meaning depends on the risk measure. Roncalli's [risk-budgeting treatment](https://arxiv.org/abs/1403.1889v1) and Richard and Roncalli's [constrained formulation](https://arxiv.org/abs/1902.05710v1) address risk allocation under explicit constraints. Our implementation measures each holding's marked distance to its initial stop plus a 1% gap allowance. That planned stop-gap amount is a sizing and monitoring proxy. It does not estimate a return distribution or place a bound on realized drawdown.

The central question is whether adding a fixed or volatility-conditioned portfolio budget changes end-of-day risk exposure and capital use, and what happens to realized NAV after the induced changes in trading. Moreira and Muir's [volatility-managed portfolios](https://onlinelibrary.wiley.com/doi/10.1111/jofi.12513) motivate examination of dynamic scaling, while this study's C rule has a different exposure metric and underlying strategy. We therefore ask: (i) how often does each policy exceed its own budget and a shared 4% reference, (ii) how does deployment change, and (iii) how do the observed NAV, drawdown and execution-cost paths differ? The proposed ordering of these outcomes is post-hoc and awaits researcher approval.

The study compares A, the baseline with a 4% new-order planning budget and no additional incumbent trim; B, which plans next-session reductions toward a fixed 4% portfolio target; and C, which applies the same trim rule with a SPY-volatility-conditioned target bounded between 2% and 5%. The original frozen FMA source remains untouched. The independent execution layer uses precomputed historical candidates and hypothetical next-open fills. This makes the comparisons auditable, while leaving full reference signal/order fidelity as an open validation task.

The record contains both a contest-capped planning scenario (V4) and a transaction-cap-neutral research scenario (V5-U), with separate accounting audits and daily outputs. The main V5-U result shows fewer own-budget breach days under B/C but worse terminal NAV and maximum drawdown than A. Reporting those movements together clarifies the limited reach of a planned-risk budget. The inspected historical window and current-constituent universe preclude an untouched out-of-sample or general performance claim.

---

## 2. Related literature

### 2.1 Risk budgets and constraints

Risk budgeting seeks to make allocation decisions in units of risk rather than capital alone. Roncalli's [2014 manuscript](https://arxiv.org/abs/1403.1889v1) provides a broad framework, and Richard and Roncalli's [2019 preprint](https://arxiv.org/abs/1902.05710v1) shows that weight constraints and turnover alter the constrained risk-budgeting problem. The present overlay is deliberately narrower: it trims integer shares against a stop-gap dollar target after planned MPB exits. Its results do not test the optimality of equal risk contributions or the theory of variance-based risk parity.

### 2.2 Dynamic exposure and momentum

Moreira and Muir [2017](https://onlinelibrary.wiley.com/doi/10.1111/jofi.12513) study volatility-managed factor portfolios. Policy C uses lagged SPY volatility to vary a stop-gap risk target, but the prior factor results do not predict the outcome of this equity strategy. Momentum studies motivate inspection of the signal pool: Jegadeesh and Titman [1993](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1993.tb04702.x) examine cross-sectional stock winners and losers, and Moskowitz, Ooi and Pedersen [2012](https://doi.org/10.1016/j.jfineco.2011.11.003) study time-series momentum in futures. MPB adds pullback and breakout conditions; its executed entries constitute a selected subset of historical candidates. Direct literature identifying the specific signal-scarcity/cash interaction in this implementation remains [CITATION NEEDED].

### 2.3 Implementation and backtest reliability

Transaction frequency matters because a rule that improves a risk metric may consume more capital in commissions and slippage. Novy-Marx and Velikov [2016](https://academic.oup.com/rfs/article-abstract/29/1/104/1844518) document trading-cost sensitivity across anomaly portfolios; this study reports modeled costs but does not assume they exhaust real implementation frictions. Brown, Goetzmann, Ibbotson and Ross [1992](https://academic.oup.com/rfs/article-abstract/5/4/553/1590264) show that survivor-conditioned samples can distort apparent performance relations. Bailey and coauthors' [2015 author-hosted manuscript](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) studies backtest overfitting. Those works support explicit treatment of current-constituent selection and prior inspection of the 282-session window, without providing a quantitative correction for either bias here.

This paper contributes a documented comparison of three fixed implementations and separates a capped planning regime from a cap-neutral research sensitivity. It reports planned-risk exposure, observed constraint exceedances, deployment and realized NAV together. The contribution is a bounded empirical account of one strategy integration, with no claim that its combination of rules is novel in the broader literature.

---

## 3. Data and methodology

### 3.1 Study sample and reference strategy

The historical window contains 282 U.S. trading sessions from 18 September 2025 through 30 October 2026. The simulation starts with $1,000,000 and uses local raw and adjusted daily OHLCV equity panels, SPY panels, a provider-action manifest, and a previously generated CSV of 1,229 candidate signal events. Raw market data are not distributed with this repository. The stock universe is a retrospectively selected set of current S&P 500 constituents, rather than point-in-time membership. Consequently, the sample is conditional on surviving constituents and is unsuitable for an unbiased historical-universe performance estimate.

The frozen FMA MPB reference defines momentum returns over 21, 63 and 126 sessions and relative-strength returns as stock return minus SPY return over the same horizons. Its score weights the sum of momentum and relative strength at those horizons by 0.25, 0.35 and 0.40. Entry qualification requires an upward EMA trend, positive 63- and 126-session momentum and relative strength, minimum liquidity and price, a stop distance between 1.5% and 10%, and either a breakout or a pullback reclaim. The breakout checks a ten-session consolidation range, a higher low, a 0.1% break above resistance and relative volume of at least 1.20. The pullback checks higher-low and EMA support, limited retreat from a recent high, a daily reclaim, and relative volume of at least 1.0. These thresholds are implementation assumptions preserved in the frozen source; they are not newly optimized for this paper.

The independent runner calls the frozen `signal_features()` on stock and SPY panels truncated at the T close. It selects entries from the existing candidate CSV, ordered by score and ticker. This avoids direct use of future rows in the inspected feature call. Complete historical candidate and order-generation parity with frozen `rankings()` and `decision()` is not established. The execution layer is a research approximation, so Policy A means the baseline *research integration* of MPB, not a certified replay of all original FMA orders.

### 3.2 Policies and portfolio risk measure

Let `P_i,t` be the raw close of holding `i`, `S_i,t` its dividend-adjusted initial stop in raw units, `q_i,t` held integer shares, and `NAV_t` marked portfolio value. The observed end-of-day stop-gap exposure is

`R_t = Σ_i q_i,t [max(0, P_i,t − S_i,t) + 0.01 P_i,t] / NAV_t`.

The 1% term is the frozen gap buffer. `R_t` measures capital notionally exposed between the mark and planned stops, with a gap allowance. It is neither a probabilistic loss forecast nor a cap on realized drawdown. A gap through a stop or a changed portfolio path can produce losses unrelated to the budget level. The comparison's `R_t` is reconstructed from executed fills and daily marks; it is distinct from the entry planner's projected risk, which also includes slippage and two commissions per new position.

Table 1 gives the policy definitions ([generated table](tables/table01_policies.md)). A retains the reference 4% new-risk planning limit and original MPB exits, with no additional trim of incumbents. B first plans MPB exits at T close, then calculates the risk of remaining incumbent shares and schedules the minimum integer reductions needed to target `b_t = 0.04`, ordered by descending risk contribution with ticker tie-break. C uses the same overlay with

`b_t = 0.04 × clip(σ_ref / σ_20,t, 0.5, 1.25)`,

where `σ_20,t` is the sample standard deviation of the latest 20 adjusted SPY close-to-close returns, annualized by `√252`, and `σ_ref` is the median 20-return SPY volatility during 2 January–29 August 2025. The stored C run has `σ_ref = 0.14485424053056145`. Thus C's budget is 2%–5%. An overlay sell is a **planned** T-close action and can execute only at the next open. The plotted budget schedule is [Figure 9](figures/fig09_policy_budgets.svg).

The frozen reference also specifies 0.5% new risk per position, a maximum of 14 holdings, a 24% sector limit, a 10% contest name limit, a 7.2% position buffer cap, and a 1% volume participation bound. Entry sizing in the research runner uses the smaller of risk, weight, sector, volume and cash limits with integer shares and a $4,000 minimum trade. Initial adjusted stops are converted to raw-price units at the signal close. The exit priority checks planned-stop breach and EMA21 trend exit before cumulative 3R/5R partial profit taking, followed by a concentration trim; the 3R and 5R cumulative sale fractions are 25% and 50%. A 408-case deterministic differential matched frozen managed-position target shares and reasons, but it does not validate the entire signal/order pipeline.

### 3.3 Timing, costs, corporate actions and regimes

Signals and exit/overlay decisions are made at T close. Hypothetical fills occur at T+1 open with adverse slippage of 5 basis points on the raw opening price and a $10 commission per fill. Same-opening sell proceeds cannot finance buys; positions are integer shares, with no leverage or partial fills. The model does not execute intraday stop orders, apply taxes, or credit cash interest to the integrated portfolio NAV. Dividend entitlement is accrued for shares held before ex-date; curated events have specified pay dates, while provider-only inferred dividends can remain unpaid receivables included in NAV. Ex-date stop adjustments are a research assumption. Unmodeled splits and other unsupported actions are not silently valued.

V4 applies a contest-derived planning threshold of `400 − 40 = 360` transactions. The check is not a hard realized-fill ceiling, and the 282-session window is longer than the original contest. V5-U replaces this threshold with a nonbinding research value of one billion to expose the policy paths without that planning restriction. All main figures and Tables 2–3 use V5-U. Table 4 reports V4 and V5-U separately; the regimes must not be pooled.

### 3.4 Outcomes and audit

The proposed primary descriptive outcomes are mean and maximum `R_t`, days above each policy's own `b_t`, maximum own-budget excess in percentage points, and days above a common 4% reference. Secondary outcomes are invested and cash fractions, realized maximum drawdown of daily NAV, fill count, modeled execution cost, and sector/name/holding exceedances. Cumulative return and Policy A entry/trade-quality diagnostics are exploratory. The hierarchy was specified after this period had already been inspected; it has not been preregistered. Drawdown uses the initial $1 million in the running peak. Sharpe values in the stored comparison use a zero risk-free rate and are descriptive only.

The numerical audit checks source hashes, 282 ordered daily rows per policy, NAV/return/drawdown recomputation and independent cash/NAV/T+1 accounting replay. Figure generation reconstructs V5-U daily risk and verifies its breach counts and mean risk against the stored independent constraint audit. These checks support numerical integrity within the model. They do not provide a causal design, a new holdout, or complete order parity.

---

## 4. Empirical results

### 4.1 Portfolio paths and realized outcomes

Table 2 ([source-linked table](tables/table02_main.md)) reports the V5-U transaction-cap-neutral comparison; [Figure 1](figures/fig01_nav.svg) plots every daily NAV observation and [Figure 2](figures/fig02_drawdown.svg) shows drawdown from the running peak. A ended at $954,598.43 (−4.5402%); B at $925,904.38 (−7.4096%); and C at $941,954.60 (−5.8045%). The corresponding maximum drawdowns were 6.0091%, 9.0257% and 8.2399%. Relative to A, B's endpoint was $28,694.06 lower and C's was $12,643.83 lower. These are conditional historical simulation differences, not estimates of expected future return.

### 4.2 Planned risk and constraint observations

The risk audit reconstructs end-of-day stop-gap exposure from filled holdings. Mean exposure was 3.8191% for A, 3.6191% for B and 4.0929% for C. A exceeded its own 4% budget on 130 sessions; B on 81; C exceeded its variable own budget on 78. [Figure 3](figures/fig03_planned_risk.svg) shows risk against each policy's budget, and Table 3 ([source-linked table](tables/table03_constraints.md)) gives counts and maximum risk. These numbers show fewer observed own-budget exceedances for the overlays, while also showing that neither overlay eliminated them. Maximum exposure reached 5.3834%, 5.3795% and 6.2915%, respectively.

A common fixed 4% reference gives a different comparison. A and B exceeded it on 130 and 81 sessions, whereas C exceeded it on 165 because C's permitted budget can be as high as 5%. [Figure 4](figures/fig04_fixed_reference.svg) shows this shared threshold. Sector weight exceeded 24% on 8, 9 and 24 sessions, respectively; no end-of-day observation exceeded the 10% name reference or 14 holdings. The audit counts are close observations, not a diagnosis of whether the excess arose during planning, at the next open, or through subsequent price movement.

### 4.3 Deployment and implementation cost

Mean invested fractions were 33.2569%, 34.5098% and 37.6113% for A, B and C. [Figures 5](figures/fig05_deployment.svg) and [10](figures/fig10_cash.svg) show invested and cash shares over time. Mean cash shares were 66.4302%, 65.1031% and 62.0110%; dividend receivables form a separate NAV component, so invested and cash shares need not sum to 100%. The higher deployment under V5-U C coincided with a worse endpoint than A, underscoring that invested fraction is not itself a measure of allocation efficiency.

A executed 313 fills, B 464 and C 478. Modeled execution costs, including $10 per fill and 5 basis points of adverse slippage, were $9,491.45, $12,675.68 and $13,336.02. [Figures 7](figures/fig07_trades.svg) and [8](figures/fig08_costs.svg) display the count and cost comparison. The larger B/C costs are measured within the simulation; without a controlled trade-level decomposition, they should not be assigned as the sole cause of the NAV differences.

### 4.4 Transaction-cap sensitivity

V4 and V5-U represent different paths and are shown separately in Table 4 ([source-linked table](tables/table04_regimes.md)). In V4, B ended at $940,072.59 (−5.9927%; 6.5576% maximum drawdown) and C at $958,904.64 (−4.1095%; 5.1563% maximum drawdown). V5-U B/C instead ended at $925,904.38 and $941,954.60. The V4 planning threshold is 360, but B/C executed 370/373 fills, so the threshold cannot be described as a strict realized-fill limit. Neither regime can be substituted for the other, and V4's higher C endpoint is not evidence that C would dominate under the cap-neutral research setting.

### 4.5 Exploratory Policy A trade diagnostics

The stored Policy A lifecycle diagnostic identifies 158 buy entries and 151 completed lifecycles, of which 47 were winners and 104 losers. Its completed-trade win rate is 31.126% and completed-trade profit factor is 0.5563, excluding dividend attribution at the lifecycle level. The raw-price P&L and dividend bridge reconciles to NAV within $0.0025 in that diagnostic. These are selected executed-entry outcomes, not the distribution of all 1,229 historical candidate signals. A separate forward-return diagnostic reports a −0.8438 percentage-point mean stock-minus-SPY return over 20 sessions for 152 uncensored A entries; its month-cluster bootstrap percentile interval is [−2.1835, 0.4138] percentage points. The intervals are exploratory, involve overlapping outcomes and only partially address dependence; no confirmatory statistical conclusion is drawn.

---

## 5. Discussion

The observed divergence between planned exposure and realized drawdown is central to the study. B's mean end-of-day stop-gap exposure and own-budget breach count were lower than A's, yet B had a larger maximum NAV drawdown. A stop-gap budget measures how much marked capital lies between current prices and specified stops under a gap allowance. Drawdown accumulates the actual sequence of marked gains and losses, including changing holdings and paths through time. The two measures answer different questions, and the simulation provides no basis for claiming that one caused the other.

The cap-neutral setting also shows that an overlay can alter future opportunity sets. A reduction frees cash only after execution; the next candidate set and its ranking can then lead to a different portfolio. B and C both executed substantially more fills than A in V5-U, while C had a higher mean invested fraction despite its dynamic risk control. The stored outputs support these path differences. They do not identify whether a particular trim, re-entry, signal-quality change or price move explains the terminal NAV ordering; that requires a dedicated, predeclared attribution analysis.

Signal scarcity provides a plausible mechanism for idle capital in an eligibility-driven strategy, but its magnitude has not been causally isolated here. The 282-session window has 1,229 reported candidates, yet entry filters, position limits, cash, current holdings and transaction-cap treatment determine which signals become fills. The Policy A trade-quality diagnostic finds weak completed-lifecycle profit factor in this inspected period. Because executed entries are selected, their 20-session forward-return comparison and overlapping observations cannot certify the full signal universe or the benefit of greater deployment.

Execution frictions move in the same direction as fill count in V5-U. B and C incurred $3,184.23 and $3,844.57 more modeled cost than A, respectively. The fixed 5-basis-point slippage and $10 commission simplify real trading; liquidity impact and partial fills could change these figures. A cost difference alone cannot account for all of the observed endpoint gaps without a paired trade-level counterfactual.

Finally, the regime comparison shows why constraints must be specified operationally. V4 uses a transaction threshold in planning, while V5-U makes that threshold nonbinding. Their B/C allocations and endpoints differ, and V4's fill counts even exceed the nominal threshold. The valid descriptive claim is that a planning rule changed simulated paths. Whether either regime satisfies contest-specific operational requirements or improves an investable strategy remains outside this analysis.

---

## 6. Limitations

The universe is retrospectively formed from current S&P 500 constituents. Securities removed before the present universe snapshot may be absent, so historical membership, signal frequency, returns and capital deployment are exposed to survivorship bias. The 282-session interval is also short for regime-general conclusions and had already been inspected before the proposed outcome hierarchy was written. No portion of this period is an untouched out-of-sample test. Post-hoc comparisons and multiple inspected diagnostics make conventional significance language especially fragile.

The simulations use daily bars and hypothetical T+1 opening fills with fixed adverse slippage and commissions. They exclude market impact, partial fills, taxes, borrow effects and intraday stop execution. The risk budget uses a planned stop-gap proxy, while reported drawdown is a realized NAV path statistic. A budget at T close does not guarantee compliance at T+1 open or at the later close. Full V5-U timing attribution of budget and sector breaches remains incomplete, and the original FMA order generator has not been shown to match every order in the independent research executor.

Corporate-action evidence remains conditional. The bundle includes provider-only dividends and unmodeled splits; V5-U held positions generated 31, 43 and 44 provisional dividend events across A, B and C. Endpoint provisional receivables of $7,164.50, $8,396.79 and $7,525.24 are included in NAV despite unverified payment dates. Removing only those endpoint components is an arithmetic sensitivity, not a full alternative portfolio path. Ex-date stop adjustments and provider action timing require further verification before strong economic conclusions.

The 408-case exit differential supports only managed-position target and reason parity under synthetic features and stubbed ranking/order generation. The external signal differential covers all reported positives but samples negatives; full order, candidate and ranking parity is untested. Any disagreement could affect subsequent holdings and reported performance. Historical forward-return horizons overlap, executed entries are selected, and month-cluster resampling only partly models dependence. The available statistical diagnostics do not establish a reliable predictive edge or a treatment effect.

The independent simulation is separate from the actual FMA StockTrak competition account. Account-level reconciliation is supplementary and cannot identify MPB-only returns without verified transaction attribution. Raw market panels, the signal CSV and provider manifest live outside this repository; a portable licensed data manifest and environment lock are still needed for third-party reproduction.

---

## 7. Conclusion

This study documents how three specified risk-budget policies behaved in one previously inspected, 282-session historical simulation. In the V5-U cap-neutral setting, the fixed and dynamic overlays had fewer end-of-day own-budget exceedances than the baseline, while both had lower terminal NAV and larger realized maximum drawdown. The result illustrates the need to report planned exposure, observed constraint conditions, capital deployment, costs and realized NAV together. It does not establish a general trade-off, a statistically significant effect or an investable return advantage.

The first manuscript can proceed as a transparent exploratory account. Before a submission-ready claim about strategy performance, the research needs bounded full signal/order fidelity checks, corporate-action and dividend resolution, constraint-timing attribution, and a reproducibility manifest. A point-in-time universe or genuinely untouched future period would be required to address external validity more directly. The original frozen FMA strategy and historical outputs remain the reference record.
