# Signal-Conditioned Portfolio Risk Budgeting: Capital Deployment, Constraint Violations, and Risk–Return Trade-offs

*Manuscript Draft V2 · 2026-11-02 · exploratory historical simulation; outcome hierarchy proposed after inspection*

## Abstract

**Background.** Portfolio risk rules act on positions that depend on when qualifying signals arrive. A tighter planned-risk target can reduce measured exposure while changing future holdings, turnover and realized losses.

**Methods.** We compare a momentum–pullback–breakout baseline (A), a fixed 4% portfolio stop-gap risk overlay (B), and a volatility-conditioned 2%–5% overlay (C) over 282 historical U.S. equity sessions from 18 September 2025 to 30 October 2026. Decisions occur at the close and hypothetical fills at the next open. The main comparison uses a transaction-cap-neutral research scenario (V5-U); the contest-capped planning regime (V4) is reported separately. The outcome hierarchy was proposed after inspecting this history.

**Results.** In V5-U, end-of-day days above each policy's own budget were 130, 81 and 78 for A, B and C. Mean invested fractions were 33.2569%, 34.5098% and 37.6113%. Ending NAVs from $1 million were $954,598.43, $925,904.38 and $941,954.60, with maximum drawdowns of 6.0091%, 9.0257% and 8.2399%. B and C used 464 and 478 fills versus A's 313, increasing modeled execution cost. C exceeded the common fixed 4% risk reference on 165 days because its own budget could rise to 5%.

**Interpretation.** The overlays had fewer own-budget exceedance days in this implementation, alongside lower reported terminal NAV and larger realized maximum drawdown than A. A sampled four-stage audit shows that a planned reduction can meet the target at the decision close yet exceed it after next-open execution. Higher invested fraction describes deployment, not efficiency. Current-constituent selection, prior inspection, hypothetical fills, provisional dividends and incomplete full order parity limit inference. These results establish no statistically significant or investable policy advantage.

---

## 1. Introduction

Portfolio managers often limit exposure before an order is placed, yet the realized path of a portfolio depends on when eligible trades become available and how existing positions evolve. A position-level rule can leave capital idle during sparse signal periods; a portfolio-level rule can force reductions in incumbents without creating new opportunities. This paper studies that interaction within one frozen momentum–pullback–breakout (MPB) research strategy. The empirical object is the allocation and risk path produced by three specified policies, rather than a search for a more profitable entry rule.

Risk budgeting provides a language for assigning exposure across positions, but its meaning depends on the risk measure. Roncalli (2014) and Richard and Roncalli (2019) discuss risk allocation under explicit constraints. Our implementation measures each holding's marked distance to its initial stop plus a 1% gap allowance. That planned stop-gap amount is a sizing and monitoring proxy. It does not estimate a return distribution or place a bound on realized drawdown.

The central question is how fixed and volatility-conditioned stop-gap budgets change observed portfolio exposure, capital deployment and implementation paths within this MPB integration. Moreira and Muir (2017) motivate examination of dynamic scaling, but their factor-volatility setting differs from our stop-gap proxy. We ask how often each policy exceeds its own budget and a shared 4% reference, how invested capital changes, and how the observed NAV, drawdown and execution-cost paths differ. The proposed ordering of these outcomes is post-hoc and awaits researcher approval. “Efficiency” remains a motivation rather than an identified outcome.

The study compares A, the baseline with a 4% new-order planning budget and no additional incumbent trim; B, which plans next-session reductions toward a fixed 4% portfolio target; and C, which applies the same trim rule with a SPY-volatility-conditioned target bounded between 2% and 5%. The original frozen FMA source remains untouched. The independent execution layer uses precomputed historical candidates and hypothetical next-open fills. A three-date reference differential now confirms exact eligible ticker lists, ranks, scores, setup labels and stop levels for 503 current-universe stocks; the first flat-account target quantities also match eight V5-U fills. Later held-portfolio orders remain uncertified, and the independent planner differs from the reference in cash and projected-risk treatment.

The record contains both a contest-capped planning scenario (V4) and a transaction-cap-neutral research scenario (V5-U), with separate accounting audits and daily outputs. The main V5-U result shows fewer own-budget breach days under B/C but worse terminal NAV and maximum drawdown than A. Reporting those movements together clarifies the limited reach of a planned-risk budget. The inspected historical window and current-constituent universe preclude an untouched out-of-sample or general performance claim.

---

## 2. Related literature

### 2.1 Risk budgets and constraints

Risk budgeting seeks to make allocation decisions in units of risk rather than capital alone. Roncalli (2014, preprint/book manuscript) provides a broad framework, and Richard and Roncalli (2019, preprint) examine constrained risk-budgeting portfolios. Their allocation concepts generally involve portfolio risk contributions under a model of return variability. Our overlay instead trims integer shares against a marked stop-gap dollar target after planned MPB exits. It neither equalizes variance contributions nor tests the optimality of risk parity. This distinction matters because a position's stop-gap contribution can rise with its marked gain even when its realized loss distribution does not change in the same way.

### 2.2 Dynamic exposure and momentum

Moreira and Muir (2017) study volatility-managed factor portfolios. Policy C uses lagged SPY volatility to vary a stop-gap target, so their factor results do not predict C's outcome. Jegadeesh and Titman (1993) examine cross-sectional stock momentum; Moskowitz, Ooi and Pedersen (2012) examine time-series momentum in futures. MPB combines momentum with pullback and breakout filters, and its executed entries are selected from a larger candidate pool. Sparse qualification can leave cash idle, yet this implementation has no identified causal estimate of that mechanism. Direct external evidence for the exact signal-scarcity and cash interaction remains [CITATION NEEDED].

### 2.3 Implementation and backtest reliability

Transaction frequency matters because a rule that improves a risk metric may incur more commissions and slippage. Novy-Marx and Velikov (2016) document trading-cost sensitivity across anomaly portfolios; this study reports modeled costs but does not assume they exhaust real frictions. Brown et al. (1992) show that survivor-conditioned samples can distort performance relations. Bailey et al. (2017), in the final *Journal of Computational Finance* publication, analyze backtest overfitting under strategy selection. Those works motivate our explicit treatment of current-constituent selection and prior inspection of the 282-session window; none supplies a numerical bias correction for this study.

The literature covers risk allocation, dynamic exposure, momentum, trading costs and backtest reliability, but does not determine how this specific stop-gap budget behaves when an MPB signal pool and an order planner interact. The paper contributes a documented comparison of three fixed implementations, separating a contest-capped planning regime from a cap-neutral sensitivity. It reports stop-gap exposure, constraint exceedances, deployment, costs and realized NAV together. This is a bounded empirical case, not a claim of a new allocation theory.

---

## 3. Data and methodology

### 3.1 Study sample and reference strategy

The historical window contains 282 U.S. trading sessions from 18 September 2025 through 30 October 2026. The simulation starts with $1,000,000 and uses local raw and adjusted daily OHLCV equity panels, SPY panels, a provider-action manifest, and a previously generated CSV of 1,229 candidate signal events. Raw market data are not distributed with this repository. The stock universe is a retrospectively selected set of current S&P 500 constituents, rather than point-in-time membership. Consequently, the sample is conditional on surviving constituents and is unsuitable for an unbiased historical-universe performance estimate.

The frozen FMA MPB reference calculates adjusted-close momentum and relative strength for \(n\in\{21,63,126\}\) sessions. With stock adjusted close \(P^{a}_{i,t}\) and adjusted SPY close \(P^{a}_{m,t}\), the implemented formulas are

\[
M_{i,t}^{(n)}=P^{a}_{i,t}/P^{a}_{i,t-n}-1,\qquad
RS_{i,t}^{(n)}=M_{i,t}^{(n)}-(P^{a}_{m,t}/P^{a}_{m,t-n}-1),
\]
\[
\operatorname{score}_{i,t}=0.25(M^{(21)}+RS^{(21)})+0.35(M^{(63)}+RS^{(63)})+0.40(M^{(126)}+RS^{(126)}).
\]

Entry qualification requires an upward EMA9/EMA21/EMA50 trend, positive 63- and 126-session momentum and relative strength, minimum liquidity and price, a stop distance between 1.5% and 10%, and either a breakout or pullback reclaim. Breakout checks a ten-session consolidation range, a higher low, a 0.1% break above resistance and relative volume at least 1.20. Pullback checks higher-low and EMA support, limited retreat from a recent high, a daily reclaim and relative volume at least 1.0. These thresholds are frozen implementation assumptions, not parameters selected for this manuscript.

The independent runner calls frozen `signal_features()` on stock and SPY panels truncated at the T close for held-position exits. Entry candidates come from the existing CSV and are ordered by descending score, then ticker. A new three-date differential calls frozen `rankings()` on all 503 current-universe symbols at the first session, a high-candidate date and the endpoint. The CSV and reference return the same 9, 40 and 21 qualified names, identical ranks, scores, setups and adjusted stops. A first-session flat-account reference decision targets the same eight tickers and share quantities as V5-U A subsequently fills. These checks support bounded feature and initial-order fidelity. They do not establish complete historical candidate/order parity, the CSV's full lineage or a point-in-time universe. Policy A therefore denotes the baseline *research integration* of MPB, not a certified replay of all original FMA orders.

### 3.2 Policies and portfolio risk measure

Let \(P_{i,t}\) be the raw close of holding \(i\), \(S_{i,t}\) its dividend-adjusted initial stop in raw units, \(q_{i,t}\) held integer shares, and \(NAV_t\) marked portfolio value. The observed end-of-day stop-gap exposure is

\[
R_t=\frac{\sum_i q_{i,t}\{\max(0,P_{i,t}-S_{i,t})+0.01P_{i,t}\}}{NAV_t}.
\]

The 1% term is the frozen gap buffer. `R_t` measures capital notionally exposed between the mark and planned stops, with a gap allowance. It is neither a probabilistic loss forecast nor a cap on realized drawdown. A gap through a stop or a changed portfolio path can produce losses unrelated to the budget level. The comparison's `R_t` is reconstructed from executed fills and daily marks; it is distinct from the entry planner's projected risk, which also includes slippage and two commissions per new position.

Table 1 gives the policy definitions ([generated table](tables/table01_policies.md)). A retains the reference 4% *new-risk planning* limit and original MPB exits, with no extra incumbent trim. B first plans MPB exits at T close, then calculates the stop-gap risk of remaining incumbent shares and schedules minimum integer reductions toward \(b_t=0.04\), ordered by descending risk contribution and ticker tie-break. C uses the same overlay with

\[
b_t=0.04\,\operatorname{clip}\!\left(\frac{\sigma_{\mathrm{ref}}}{\sigma_{20,t}},0.5,1.25\right),
\qquad 0.02\leq b_t\leq0.05,
\]

where \(\sigma_{20,t}\) is the sample standard deviation of the latest 20 adjusted SPY close-to-close returns, annualized by \(\sqrt{252}\), and \(\sigma_{\mathrm{ref}}\) is the median 20-return SPY volatility during 2 January–29 August 2025. The stored C run has \(\sigma_{\mathrm{ref}}=0.14485424053056145\). An overlay sell is **planned** at T close and can execute only at the next open. The budget schedule is [Figure 9](figures/fig09_policy_budgets.svg).

The frozen reference also specifies 0.5% new risk per position, at most 14 holdings, a 24% sector limit, a 10% contest name limit, a 7.2% position buffer cap, and a 1% volume participation bound. Entry sizing in the research runner takes the integer minimum of risk, weight, sector, volume and cash limits and enforces a $4,000 minimum trade. The risk term includes 1% gap allowance, 5 basis points of assumed adverse entry slippage and two commissions in the projected new-position charge. Initial adjusted stops convert to raw-price units at the signal close. The exit priority checks planned-stop breach and EMA21 trend exit before cumulative 3R/5R partial profit taking, followed by a concentration trim; the 3R and 5R cumulative sold fractions are 25% and 50%. A persistent 408-case differential matched frozen managed-position target shares and reasons. Unlike frozen `decision()`, the independent V5-U planner does not credit planned sell proceeds or released incumbent risk to new buys before those sells fill. This conservative cash/risk treatment can change later orders, so full order parity remains open.

### 3.3 Timing, costs, corporate actions and regimes

Signals and exit/overlay decisions are made at T close. Hypothetical fills occur at T+1 open. A buy uses \(P^{\mathrm{open}}(1+0.0005)\), a sell uses \(P^{\mathrm{open}}(1-0.0005)\), and each fill pays $10 commission. The modeled per-fill cost is \(10+0.0005qP^{\mathrm{open}}\). Same-opening sell proceeds cannot finance buys; positions use integer shares, with no leverage or partial fills. The model does not execute intraday stops, apply taxes or credit cash interest to integrated NAV. Dividend entitlement is accrued for shares held before ex-date. Two curated events (USB and CAT) have recorded declarations and payment dates; provider-only inferred amounts remain unpaid receivables in NAV and cannot be spent. Ex-date stop reductions are a model assumption. The runner rejects unsupported splits and other actions that affect held or pending symbols; this does not independently verify every corporate action in the universe.

V4 applies a contest-derived planning threshold of `400 − 40 = 360` transactions. The check is not a hard realized-fill ceiling, and the 282-session window is longer than the original contest. V5-U replaces this threshold with a nonbinding research value of one billion to expose the policy paths without that planning restriction. All main figures and Tables 2–3 use V5-U. Table 4 reports V4 and V5-U separately; the regimes must not be pooled.

### 3.4 Outcomes and audit

The proposed primary descriptive outcomes are mean and maximum \(R_t\), days above each policy's own \(b_t\), maximum own-budget excess in percentage points, and days above a common 4% reference. Secondary outcomes are capital deployment, realized drawdown, fill count, modeled execution cost, and sector/name/holding exceedances. Let \(C_t\) be spendable cash and \(D_t\) the dividend receivable. Invested fraction is

\[
I_t=\frac{NAV_t-C_t-D_t}{NAV_t},\qquad
\mathrm{DD}_t=1-\frac{NAV_t}{\max(NAV_0,NAV_1,\ldots,NAV_t)}.
\]

These implemented definitions measure deployment level and realized path drawdown. They do not identify *deployment efficiency* or a causal return per available opportunity. Mean cash share is \(C_t/NAV_t\). Cumulative return and Policy A entry/trade diagnostics are exploratory. The outcome hierarchy was proposed after this period had already been inspected and awaits researcher approval. Stored Sharpe values use a zero risk-free rate and are descriptive only.

The numerical audit checks source hashes, 282 ordered daily rows per policy, NAV/return/drawdown recomputation and independent cash/NAV/T+1 accounting replay. Figure generation reconstructs V5-U daily risk and verifies breach counts and mean risk against the stored independent constraint audit. The bounded differential and sampled four-stage timing replay are documented separately. These checks support numerical integrity within the model. They do not provide a causal design, a new holdout or complete order parity. Daily policy paths share dates but are serially dependent; no 282-independent-replication interpretation or confirmatory p-value is used.

---

## 4. Empirical results

### 4.1 Portfolio paths and realized outcomes

Table 2 ([source-linked table](tables/table02_main.md)) reports the V5-U transaction-cap-neutral comparison; [Figure 1](figures/fig01_nav.svg) plots every daily NAV observation and [Figure 2](figures/fig02_drawdown.svg) shows drawdown from the running peak. A ended at $954,598.43 (−4.5402%); B at $925,904.38 (−7.4096%); and C at $941,954.60 (−5.8045%). The corresponding maximum drawdowns were 6.0091%, 9.0257% and 8.2399%. Relative to A, B's endpoint was $28,694.06 lower and C's was $12,643.83 lower. These are conditional historical simulation differences, not estimates of expected future return.

### 4.2 Planned risk and constraint observations

The risk audit reconstructs end-of-day stop-gap exposure from filled holdings. Mean exposure was 3.8191% for A, 3.6191% for B and 4.0929% for C. A exceeded its own 4% budget on 130 sessions; B on 81; C exceeded its variable own budget on 78. [Figure 3](figures/fig03_planned_risk.svg) shows risk against each policy's budget, and Table 3 ([source-linked table](tables/table03_constraints.md)) gives counts and maximum risk. These numbers show fewer observed own-budget exceedances for the overlays, while also showing that neither overlay eliminated them. Maximum exposure reached 5.3834%, 5.3795% and 6.2915%, respectively.

A common fixed 4% reference gives a different comparison. A and B exceeded it on 130 and 81 sessions, whereas C exceeded it on 165 because C's permitted budget can be as high as 5%. [Figure 4](figures/fig04_fixed_reference.svg) shows this shared threshold. Sector weight exceeded 24% on 8, 9 and 24 sessions, respectively; no end-of-day observation exceeded the 10% name reference or 14 holdings. The audit counts are close observations. The bounded [timing table](tables/v2/table01_risk_timing.md) and [V2 Figure 1](figures/v2/fig01_timing.svg) show selected transitions: on B's 23 October 2025 breach, observed T-close risk was 5.3795%, the T-price hypothetical state after the next-session overlay sell was 3.9972%, but the actual simulated post-fill open risk was 4.3026% and the next close risk 4.1652%. The corresponding C values were 5.6817%, 4.3237%, 4.7080% and 4.5116%, against a T target of 4.3272%. The sampled price transitions show why a T-close trim plan is not executed compliance; they do not explain every breach.

### 4.3 Deployment and implementation cost

Mean invested fractions were 33.2569%, 34.5098% and 37.6113% for A, B and C. [Figures 5](figures/fig05_deployment.svg) and [10](figures/fig10_cash.svg) show invested and cash shares over time. Mean cash shares were 66.4302%, 65.1031% and 62.0110%; receivables are a separate NAV component. The [V2 deployment table](tables/v2/table02_deployment.md) combines these observables with candidate availability, fill count and cost. Candidate count is a pre-portfolio signal measure, not a count of executable opportunities after constraints. The higher deployment under C coincided with a worse endpoint than A. Neither fact estimates allocation efficiency.

A executed 313 fills, B 464 and C 478. Modeled execution costs, including $10 per fill and 5 basis points of adverse slippage, were $9,491.45, $12,675.68 and $13,336.02. [Figures 7](figures/fig07_trades.svg) and [8](figures/fig08_costs.svg) display the count and cost comparison. The larger B/C costs are measured within the simulation; without a controlled trade-level decomposition, they should not be assigned as the sole cause of the NAV differences.

### 4.4 Corporate-action sensitivity

The two curated dividend events generated $404.63, $490.70 and $489.19 of simulated accrual for A/B/C. Provider-only provisional events generated endpoint unpaid receivables of $7,164.50, $8,396.79 and $7,525.24. The combined simulated accrual is $7,569.13, $8,887.49 and $8,014.43, respectively; only the curated event metadata have separate declaration and payment-date records. The [V2 dividend table](tables/v2/table03_dividends.md) separates these classes. Subtracting *only* the endpoint provisional receivable gives A $947,433.93, B $917,507.59, C $934,429.36, preserving the arithmetic A > C > B order. This narrow component test does not reproduce a path with different cash, sizing, stops and fills. It does not resolve dividend uncertainty or establish a bound on full-path NAV.

### 4.5 Transaction-cap sensitivity

V4 and V5-U represent different paths and are shown separately in Table 4 ([source-linked table](tables/table04_regimes.md)). In V4, B ended at $940,072.59 (−5.9927%; 6.5576% maximum drawdown) and C at $958,904.64 (−4.1095%; 5.1563% maximum drawdown). V5-U B/C instead ended at $925,904.38 and $941,954.60. The V4 planning threshold is 360, but B/C executed 370/373 fills, so the threshold cannot be described as a strict realized-fill limit. Neither regime can be substituted for the other, and V4's higher C endpoint is not evidence that C would dominate under the cap-neutral research setting.

### 4.6 Exploratory Policy A trade diagnostics

The stored Policy A lifecycle diagnostic identifies 158 buy entries and 151 completed lifecycles, of which 47 were winners and 104 losers. Its completed-trade win rate is 31.126% and completed-trade profit factor is 0.5563, excluding dividend attribution at the lifecycle level. The raw-price P&L and dividend bridge reconciles to NAV within $0.0025 in that diagnostic. These are selected executed-entry outcomes, not the distribution of all 1,229 historical candidate signals. A separate forward-return diagnostic reports a −0.8438 percentage-point mean stock-minus-SPY return over 20 sessions for 152 uncensored A entries; its month-cluster bootstrap percentile interval is [−2.1835, 0.4138] percentage points. The intervals are exploratory, involve overlapping outcomes and only partially address dependence; no confirmatory statistical conclusion is drawn.

---

## 5. Discussion

The observed divergence between stop-gap exposure and realized drawdown is central to the study. B's mean end-of-day proxy and own-budget breach count were lower than A's, yet B had a larger maximum NAV drawdown. The proxy adds marked distances to initial stops with a fixed gap allowance. Drawdown accumulates the actual sequence of marked gains and losses as holdings and prices change. A stop can be crossed, delayed or followed by a different opportunity path. The two measures answer different questions. The sampled timing reconstruction adds a narrower observation: an integer-share reduction planned to fall under the target at T prices can still leave realized post-fill exposure above it after an opening gap. It does not identify the cause of every daily breach.

The cap-neutral setting also shows that an overlay changes future holdings. A reduction frees cash only after execution; the next candidate set and its ranking can then lead to a different portfolio. B and C executed substantially more fills than A, while C had a higher mean invested fraction despite its dynamic budget. These are observed path differences. They do not identify whether particular trims, re-entries, signal quality, price moves or costs explain the terminal ordering. The independent order planner's treatment of pending sells differs from the frozen reference: it withholds sell proceeds and incumbent risk release from new-buy planning. That implementation choice may affect later allocations and limits the claim that the result is a pure reference-strategy overlay comparison.

Signal scarcity is a plausible source of idle cash in an eligibility-driven strategy, but its magnitude has not been isolated. The 282-session window has 1,229 reported candidates; a candidate is not automatically feasible after holdings, sector, risk, cash and volume checks. The Policy A completed-lifecycle profit factor is weak in this inspected period, but executed entries are selected. Their overlapping 20-session forward-return comparisons cannot certify the full signal pool or the value of greater investment exposure. This is why V2 calls the measured outcome *capital deployment* and leaves *deployment efficiency* unresolved.

Execution frictions move in the same direction as fill count in V5-U. B and C incurred $3,184.23 and $3,844.57 more modeled cost than A, respectively. The fixed 5-basis-point slippage and $10 commission simplify real trading; liquidity impact and partial fills could change these figures. A cost difference alone cannot account for all of the observed endpoint gaps without a paired trade-level counterfactual.

The regime comparison shows why constraints must be specified operationally. V4 uses a transaction threshold in planning, while V5-U makes it nonbinding. Their B/C allocations and endpoints differ, and V4 fill counts exceed its nominal threshold. The observed paths depend on the planning regime. Whether either satisfies competition operations or improves an investable strategy remains outside this analysis. The paired dates permit descriptive comparison but represent one dependent historical market path; the existing bootstrap diagnostic does not warrant a statistical superiority claim.

---

## 6. Limitations

The universe is retrospectively formed from current S&P 500 constituents. Securities removed before the present universe snapshot may be absent, so historical membership, signal frequency, returns and capital deployment are exposed to survivorship bias. The 282-session interval is also short for regime-general conclusions and had already been inspected before the proposed outcome hierarchy was written. No portion of this period is an untouched out-of-sample test. Post-hoc comparisons and multiple inspected diagnostics make conventional significance language especially fragile.

The simulations use daily bars and hypothetical T+1 opening fills with fixed adverse slippage and commissions. They exclude market impact, partial fills, taxes, borrow effects and intraday stop execution. The budget uses a planned stop-gap proxy; drawdown is a realized NAV path statistic. A target at T close does not guarantee compliance at T+1 open or later close. The new sample illustrates this mechanism but does not classify every budget or sector exceedance. The original FMA order generator has not been shown to match every order in the independent research executor; its projected cash and risk treatment differs from V5-U.

Corporate-action evidence remains conditional. The bundle includes provider-only dividends and unsupported splits; V5-U held positions generated 31, 43 and 44 provisional provider-only events across A, B and C. Their endpoint unpaid receivables of $7,164.50, $8,396.79 and $7,525.24 enter NAV despite unverified payment dates. Two curated events provide smaller independently registered accruals. Removing endpoint provisional components is arithmetic sensitivity only. Earlier accruals can affect NAV denominators, sizing and later orders, so no full-path bound follows. Ex-date stop adjustments and provider action timing require further verification before strong economic conclusions.

The 408-case exit differential supports only managed-position target and reason parity under synthetic features and stubbed ranking/order generation. Three new full-universe dates show exact candidate/rank/score/stop agreement and the first flat-account decision agrees on eight target quantities. The external signal differential covers all reported positives but samples negatives; later held-portfolio order parity remains untested. Any disagreement could alter subsequent holdings and reported performance. Forward-return horizons overlap, executed entries are selected, and month-cluster resampling only partly models dependence. The available diagnostics do not establish predictive edge or a treatment effect.

The independent simulation is separate from the actual FMA StockTrak competition account. Account-level reconciliation is supplementary and cannot identify MPB-only returns without verified transaction attribution. Raw market panels, the signal CSV and provider manifest live outside this repository; a portable licensed data manifest and environment lock are still needed for third-party reproduction.

---

## 7. Conclusion

This study documents how three specified budget policies behaved in one previously inspected, 282-session historical simulation. In V5-U, the fixed and dynamic overlays had fewer end-of-day own-budget exceedances than A, while both had lower terminal NAV and larger realized maximum drawdown. A bounded timing reconstruction shows that a planned T-close reduction can meet its target at T marks yet leave post-fill exposure above it. The study therefore reports stop-gap exposure, observed constraints, deployment, costs and realized NAV together. It establishes no general risk-return trade-off, statistically significant effect, capital-allocation efficiency or investable advantage.

This revised manuscript is a transparent exploratory account. Stronger strategy-performance conclusions require later-state signal/order fidelity, independent corporate-action verification, complete breach attribution and a point-in-time universe or genuinely untouched future period. The original frozen FMA source and historical A/B/C outputs remain the reference record.

---

## References

Bailey, D. H., Borwein, J. M., López de Prado, M., and Zhu, Q. J. (2017). The probability of backtest overfitting. *Journal of Computational Finance*, 20(4). [doi:10.21314/jcf.2016.322](https://doi.org/10.21314/jcf.2016.322).

Brown, S. J., Goetzmann, W., Ibbotson, R. G., and Ross, S. A. (1992). Survivorship bias in performance studies. *The Review of Financial Studies*, 5(4), 553–580. [doi:10.1093/rfs/5.4.553](https://doi.org/10.1093/rfs/5.4.553).

Jegadeesh, N., and Titman, S. (1993). Returns to buying winners and selling losers: Implications for stock market efficiency. *The Journal of Finance*, 48(1), 65–91. [doi:10.1111/j.1540-6261.1993.tb04702.x](https://doi.org/10.1111/j.1540-6261.1993.tb04702.x).

Moreira, A., and Muir, T. (2017). Volatility-managed portfolios. *The Journal of Finance*, 72(4), 1611–1644. [doi:10.1111/jofi.12513](https://doi.org/10.1111/jofi.12513).

Moskowitz, T. J., Ooi, Y. H., and Pedersen, L. H. (2012). Time series momentum. *Journal of Financial Economics*, 104(2), 228–250. [doi:10.1016/j.jfineco.2011.11.003](https://doi.org/10.1016/j.jfineco.2011.11.003).

Novy-Marx, R., and Velikov, M. (2016). A taxonomy of anomalies and their trading costs. *The Review of Financial Studies*, 29(1), 104–147. [doi:10.1093/rfs/hhv063](https://doi.org/10.1093/rfs/hhv063).

Richard, J.-C., and Roncalli, T. (2019). Constrained risk budgeting portfolios: Theory, algorithms, applications & puzzles. [arXiv:1902.05710](https://arxiv.org/abs/1902.05710), preprint.

Roncalli, T. (2014). Introduction to risk parity and budgeting. [arXiv:1403.1889](https://arxiv.org/abs/1403.1889), preprint/book manuscript.
