# Planned Risk Budgets, Executed Exposure, and Capital Deployment in a Signal-Driven Equity Portfolio

*Manuscript V4.1 · major revision for internal academic review · 3 November 2026*  
*Research variant: NG-SF-270-LW, approved protocol V0.3. All results are historical simulations, not live returns.*

## Abstract

Portfolio risk budgets are assigned when orders are planned, whereas the risk exposure subsequently observed depends on opening prices, fills, costs, corporate actions, and closing valuation. We study this distinction in a signal-driven U.S. equity portfolio using a point-in-time Norgate constituent universe and four prespecified policies over 230 sessions from 2 December 2025 through 30 October 2026. The single locked primary comparison is Policy B minus Policy A in mean positive closing stop-gap exposure above a common 4% reference. The estimated difference is −0.001127 exposure fraction (−11.27 basis points of net asset value); the prespecified 95% circular block-bootstrap percentile interval is [−0.002050, −0.000357], using 20-session blocks and 10,000 replicates. This interval is conditional on an already inspected historical window and a modeled risk proxy; no separate hypothesis test is reported. Across 229 decision/open pairs, 60 compliant B plans exceed their decision budget at the next open. Mean invested capital is 33.31% of net asset value for A and 33.48% for B. An exact symmetric accounting identity assigns their −19.92 basis point difference in mean closing modeled risk to a +1.98 basis point deployment component and a −21.91 basis point risk-per-invested-capital component; these are not causal overlay effects. B trades more, incurs higher modeled costs, and has a less negative simulated cumulative return than A, but all four policy returns are negative. The primary difference is concentrated in several months, especially June 2026. The findings support a narrow historical statement about modeled exposure and document the limits of decision-time compliance, without establishing live profitability, return superiority, or out-of-sample policy effects.

**Keywords:** portfolio risk budgets; execution timing; stop-gap exposure; capital deployment; historical simulation; block bootstrap.

## 1. Introduction

A decision-time risk target governs an intended portfolio, while the portfolio held after execution is valued at different prices and after transaction costs. Treating those states as interchangeable can conceal a material implementation gap. This paper measures that gap and examines whether a lower modeled risk path is associated with less capital deployment, a different composition of invested assets, or both. The question is relevant to signal-driven systems in which a risk overlay trims incumbent positions before new buys are planned.

We define risk as a transparent, share-level marked stop-gap exposure, not as a loss quantile. The measure adds the marked distance above an adjusted initial stop to a fixed 1% price buffer and divides the resulting dollar amount by net asset value (NAV). This permits exact accounting at the decision close, before fills, after fills, and at the subsequent close. It cannot guarantee execution at a stop or bound drawdown. Our contribution is therefore a staged, audited description of a portfolio-risk rule rather than a claim that the rule controls realized loss.

The empirical setting is an approved, sector-free Norgate research variant of a momentum–pullback–breakout (MPB) integration. Policy A retains the baseline exit and order planner without an incumbent overlay. B adds a fixed 4% incumbent stop-gap trim. C applies the same trim with a volatility-conditioned budget bounded between 2% and 5%. F applies that trim at a fixed pre-study comparator budget. The policies share signal, execution, accounting, and data rules, but their realized portfolios diverge. Consequently, matched policy paths are informative descriptions rather than randomized treatment assignments.

### 1.1 Research Gap and Contributions

A rule designed to keep an incumbent portfolio near 4% modeled exposure is expected to reduce exceedance of a 4% reference when it trims positions successfully. Finding a lower B-than-A mean on that same threshold is therefore partly built into the policy comparison; by itself, it is neither a surprising discovery nor evidence that the rule protects future wealth. The nontrivial empirical question is what the planned constraint becomes after the intervening market and accounting events, and what economic information is lost when a closing risk statistic is presented without the corresponding capital and order paths.

This study makes four bounded contributions. First, it archives the complete S2 final plan before next-day information and compares it with pre-fill S3, post-fill S4, and closing S5 exposure. Second, it quantifies how often a decision-compliant plan is above its own decision budget at the opening, keeping overnight valuation separate from fill-stage and later closing changes. Third, it measures invested capital and uses an exact symmetric identity to describe how deployment and risk per invested dollar combine in observed policy differences. Fourth, it exposes what the journals cannot identify: unrecorded qualifying candidates, unique causes within composite order rejections, and causal counterfactuals for the overlay. These contributions concern implementation measurement and reproducibility, not a new general theory of portfolio risk.

The single locked primary estimand compares B with A on positive **closing** exposure above a common 4% reference. Decision/open gaps, cash use, portfolio composition, trading, NAV, and C/F comparisons are secondary descriptions. The protocol and code identities were locked before the **official Batch 4B experiment**, but the 2025–2026 window had already been examined during project development. This is neither an independently preregistered study of an untouched sample nor an independent holdout. That distinction governs the bootstrap interpretation and the prominence given to adverse outcomes, including negative simulated returns under every policy.

## 2. Related Literature

### 2.1 Risk budgets, stop rules, and signal portfolios

Risk-budgeting research formalizes allocation under a chosen risk measure and explicit constraints ([Roncalli, 2014](https://arxiv.org/abs/1403.1889); [Richard and Roncalli, 2019](https://arxiv.org/abs/1902.05710)). The present additive stop-gap measure is more directly auditable at the share level than a covariance-based contribution, but the two quantities answer different questions. A rising mark can increase stop-gap exposure while a fixed initial stop remains unchanged; the measure is not a forecast of loss probability. This paper's contribution is to examine its value at successive implementation states, rather than to propose a general alternative to established risk-budgeting theory.

The stop-loss literature likewise does not imply that a rule must improve expected returns or realized downside. [Kaminski and Lo (2014)](https://dspace.mit.edu/entities/publication/bb69ca4b-0cdc-487f-831d-63b2e84fafee) analyze exposure-reducing stop-loss policies and show that their value depends on the return process and the chosen rule. Their policies are triggered by accumulated portfolio losses, whereas the present overlay trims a marked distance-to-stop proxy before next-open execution. This difference prevents direct transfer of their performance results. [Moreira and Muir (2017)](https://onlinelibrary.wiley.com/doi/10.1111/jofi.12513) provide context for state-dependent exposure, but Policy C's lagged-volatility target is not a replication of their factor strategy. Cross-sectional and time-series momentum studies ([Jegadeesh and Titman, 1993](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1993.tb04702.x); [Moskowitz, Ooi, and Pedersen, 2012](https://www.sciencedirect.com/science/article/pii/S0304405X11002613)) motivate attention to trend signals without validating this MPB filter.

### 2.2 Execution and implementation costs

The execution literature makes clear why a planned portfolio is not an implemented one. [Almgren and Chriss (2001)](https://www.risk.net/journal-risk/2161150/optimal-execution-portfolio-transactions) model a trade-off between execution uncertainty and temporary or permanent market impact. Their framework highlights a component absent here: the Batch 4B executor imposes fixed adverse slippage and a commission but no endogenous market impact or optimized execution trajectory. [Novy-Marx and Velikov (2016)](https://academic.oup.com/rfs/article/29/1/104/1844518) demonstrate why trading costs matter when interpreting strategy returns. Neither source justifies treating a difference between S2 and S4 as pure slippage; the stages also differ in prices, holdings, actions and NAV.

### 2.3 Dependent inference and data reuse

[Künsch (1989)](https://projecteuclid.org/journals/annals-of-statistics/volume-17/issue-3/The-Jackknife-and-the-Bootstrap-for-General-Stationary-Observations/10.1214/aos/1176347265.full) develops bootstrap reasoning for dependent stationary observations, while [Politis and Romano (1992)](https://statistics.stanford.edu/technical-reports/circular-block-resampling-procedure-stationary-data) describe circular block resampling. Their work motivates resampling adjacent days rather than treating 230 closes as independent, but it does not establish stationarity in this short policy path. [White (2000)](https://onlinelibrary.wiley.com/doi/10.1111/1468-0262.00152) studies the inferential problem created by repeated use of data for model selection; the present paper does not implement White's reality-check test. [Bailey et al. (2017)](https://www.risk.net/journal-of-computational-finance/2471206/the-probability-of-backtest-overfitting) supply related backtest-selection context, and [Brown et al. (1992)](https://academic.oup.com/rfs/article-abstract/5/4/553/1590264) document how survivorship truncation can distort performance studies. The point-in-time universe addresses one source of retrospective selection, but prior inspection of this window and data-vintage constraints remain.

## 3. Research Questions

**RQ1 (locked primary):** Over the fixed 230-session calendar, what is B minus A in mean daily positive closing stop-gap exposure above a **common 4% reference**? The approved protocol names this single comparison before the official Batch 4B run. A's common-reference excess is not an incumbent-overlay compliance failure because A has no such overlay.

**RQ2 (implementation):** How do final planned exposure at decision close (S2), pre-fill opening exposure (S3), post-fill opening exposure (S4), and subsequent closing exposure (S5) differ? The S2-to-S4 compliance indicator retains the decision-date budget, including for C.

**RQ3 (economic description):** How do deployment, risk per invested dollar, holdings, turnover, modeled costs, and simulated NAV differ across policies? Which mechanisms are directly recorded, which are accounting reconstructions, and which remain unidentified? RQ2 and RQ3 do not support secondary significance or causal claims.

## 4. Data

The approved experiment uses a Norgate-defined daily S&P 500 constituent universe with observed former members and stable private security identifiers. The acquired extraction provides raw `NONE` prices for valuation and fills, `TOTALRETURN` bars for signal price normalization, and `CAPITAL` bars for volume normalization. At each decision date, only information available through that date enters the signal computation. A stock requires 270 valid stock/SPY dates aligned through the decision close; a member lacking that history remains in the universe but cannot generate a signal. The first eligible study session is 2 December 2025. All policies begin with $1,000,000 cash and no holdings or receivables. The common calendar ends on 30 October 2026, giving **230 closing observations: one initial portfolio state and 229 subsequent next-close S5 states**. Each of the first 229 decision closes has a next-open pair; the terminal close has no invented following pair. Thus the primary closing series contains the initial state even though it is not an S5 snapshot.

The empirical source is the official Batch 4B result and append-only decision, order, and snapshot journals. The official audit reports 230 valid closes, 229 valid pairs, 1,374 stage snapshots per policy, and PASS accounting reconciliation for A/B/C/F. Subsequent Batch 4C analyses used these original records without rerunning a strategy. The study is limited to the acquired data vintage and the vendor's constituent definition; point-in-time membership improves on a current-constituent retrospective screen but does not establish historical-vintage equivalence to a fully archived market database.

Corporate-action accounting follows the approved private event register. Verified cash dividends create receivables for entitled holdings and become spendable on documented payment dates; adjusted stops retain raw-share consistency. Material unsupported actions block the affected run rather than being silently valued. The official approval record binds the protocol file's exact hash and separately approved accounting/source-precision judgments. The protocol document retains preapproval draft language as an immutable file; the dated private approval record, not an edit to that file, authorizes the official experiment. Alternative event timing and cash conventions were not simulated.

## 5. Methodology

### 5.1 Policies and event sequence

Policy A is the sector-free MPB baseline with a 4% **new-order planning** budget and no incumbent overlay. B applies an additional incumbent trim targeting 4%. C uses the same trim at \(b_T=0.04\operatorname{clip}(\sigma_{ref}/\sigma_{20,T},0.5,1.25)\), with a 2%–5% bound. Here \(\sigma_{20,T}\) is the annualized sample standard deviation of 20 lagged SPY total-return close-to-close returns through T, and \(\sigma_{ref}=0.14485371463395177\) is the median of 165 pre-study volatility observations. F applies B's trim rule at a constant 3.8654080953% budget, the arithmetic mean of C's formula on those same pre-study observations. F was fixed before study-window outcomes and is a secondary mechanism comparator. All four policies omit sector caps by design; this is a named research variant, not an exact order-for-order reproduction of the older frozen FMA strategy.

At T close, S0 records the actual portfolio; S1 follows MPB exits and any overlay sells; S2 records the final accepted plan, including buys. S2 is persisted before T+1 prices are consumed. At T+1 open, documented payments and actions precede S3; whole-order sells then buys precede post-fill S4; S5 marks the next close. Fills use raw open with five basis points of adverse slippage and $10 commission per fill. Same-opening sell proceeds cannot finance buys. The model has integer shares, no partial fills, no intraday stop execution, and no taxes, market impact, or cash interest. Opening buy eligibility uses pre-fill spendable cash. Costs and receivables remain separate from invested assets.

### 5.2 Exposure, estimand, and inference

For position \(i\) in stage \(s\), let \(q_{i,s}\) denote raw shares, \(P_{i,s}\) the raw mark, \(S_{i,s}\) its action-adjusted raw stop, and \(NAV_s\) net asset value. The modeled exposure fraction is

\[
R_s=\frac{\sum_i q_{i,s}\{\max(0,P_{i,s}-S_{i,s})+0.01P_{i,s}\}}{NAV_s}.
\]

Let \(R_{p,t}^{close}\) denote the recorded closing risk, equal to the initial all-cash state for \(t=1\) and the S5 snapshot risk for the following 229 dates. At each closing date \(t\), define \(X_{p,t}=\max(R_{p,t}^{close}-0.04,0)\). The **locked primary statistic** is

\[
\widehat\Delta_{B-A}=\frac{1}{230}\sum_{t=1}^{230}(X_{B,t}-X_{A,t}).
\]

The fixed reference is 4% for both policies, regardless of C's and F's policy-specific budgets. B's 4% incumbent trim directly targets this exposure measure, so a lower B value of the positive-excess statistic is partly expected from the imposed rule when the trim is feasible. The comparison is nevertheless empirical because later prices, fills, costs and subsequent holdings can alter the closing path; its sign alone is not evidence of a novel economic law or future downside protection.

The primary interval is the approved 95% circular block-bootstrap percentile interval for the **paired** 230-date difference series: 20-session blocks, 10,000 replicates, seed 20261102. Each replicate samples block starts with replacement, wraps at the calendar endpoint, truncates to 230 dates, and recomputes the mean. Block lengths 10 and 40 are prespecified sensitivity checks. The protocol was locked before the official experiment, but the underlying historical window had already been inspected; no independent preregistration or untouched sample is claimed. Exact reproduction of the PCG64 replicate hashes verifies **computation**, not stationarity, interval coverage under regime change, independence from prior selection, or the validity of the risk proxy. The interval is conditional historical evidence, not a separately conducted null-hypothesis test; no p-value is reported. Short-sample dependence and the concentration of the observed contrast in June 2026 further constrain inference.

### 5.3 Secondary accounting and outcomes

The implementation gap is \(G_{p,T}=R_{p,T+1}^{S4}-R_{p,T}^{S2}\), with positive part \(\max(G_{p,T},0)\). A compliant-plan-to-opening-exceedance event requires \(R_{S2}\le b_T+10^{-9}\) and \(R_{S4}>b_T+10^{-9}\). The decision-date budget \(b_T\) governs this indicator; S5 also retains its newly calculated closing budget. The exact stage identity \((R_{S3}-R_{S2})+(R_{S4}-R_{S3})+(R_{S5}-R_{S4})=R_{S5}-R_{S2}\) separates accounting intervals without identifying a particular cause of a movement.

At a close, define invested fraction \(D=(NAV-\text{cash}-\text{receivables})/NAV\) and risk per invested dollar \(Q=R/D\) when \(D>0\). For policies X and Y with positive investment, their observed risk difference has the exact symmetric decomposition

\[
R_X-R_Y=(D_X-D_Y)\frac{Q_X+Q_Y}{2}+(Q_X-Q_Y)\frac{D_X+D_Y}{2}.
\]

The two terms are deployment and risk-per-invested-capital **accounting components**, not causal effects. The shared initial all-cash close has \(D=R=0\) for all policies; \(Q\) is undefined there and both components are set to zero by explicit convention. The remaining 229 closes per pair have positive investment. Other secondary outcomes are spendable cash, receivables, position count, position-value concentration, gross traded notional, modeled costs, NAV, cumulative return, and maximum drawdown. All new policy contrasts in these outcomes are descriptive.

## 6. Empirical Results

### 6.1 Primary common-reference risk comparison

**Table 1. Official Batch 4B closing outcomes.** Positive excess is shown in **basis points of NAV exposure** (1 bp = 0.0001 exposure fraction), not return or transaction-cost basis points. Return and drawdown are simulated percentages. Common-reference exceedance days use all 230 closes, including the initial all-cash state. Source: official Batch 4B [`policy_summary.csv`](../restricted_norgate/batch4b_official_20261102/policy_summary.csv) and [`summary.json`](../restricted_norgate/batch4b_official_20261102/summary.json).

| Policy | Mean positive excess over 4% (bp of NAV exposure) | Days above 4% / 230 | Mean invested fraction | Cumulative return | Maximum drawdown | Final NAV |
|:--|--:|--:|--:|--:|--:|--:|
| A | 17.63 | 90 / 230 | 33.31% | −6.14% | −9.22% | $938,574.53 |
| B | 6.36 | 66 / 230 | 33.48% | −4.84% | −7.99% | $951,609.08 |
| C | 40.21 | 135 / 230 | 38.36% | −6.80% | −10.64% | $931,997.66 |
| F | 3.16 | 35 / 230 | 32.51% | −5.31% | −7.92% | $946,945.04 |

B's mean positive closing excess is lower than A's by −0.001127123788 exposure fraction, or −0.1127 percentage points (−11.27 basis points of NAV). This is the approved primary comparison, not a return comparison. The 95% block-20 interval is [−0.002050272859, −0.000357213419]. The 10-session and 40-session intervals are [−0.001973703191, −0.000448824667] and [−0.002016367304, −0.000290831932], respectively. Exact PCG64 replicate hashes were independently reproduced for all three lengths in Batch 4C.4. These intervals are below zero under their respective resampling procedures; their interpretation remains conditional on the model and inspected historical period. No statistical claim is made about C or F, and no p-value is inferred from the intervals.

![Figure 1. Modeled NAV paths by policy, U.S. dollars, 230 closes.](../restricted_norgate/batch4b_official_20261102/nav_paths.svg)

**Figure 1.** Modeled NAV paths in U.S. dollars over the common 230-session calendar. All four policies end below the initial $1 million. Source: official Batch 4B `nav_paths.svg`; the figure is not evidence of live trading returns.

### 6.2 Decision and execution states

**Table 2. S2-to-S4 implementation gaps.** Means are basis points of NAV exposure over 229 decision/open pairs per policy. A's 4% reference is not an incumbent-overlay obligation. Source: Batch 4C.1 [`distributions.csv`](../restricted_norgate/batch4c1_implementation_gap/distributions.csv), [`strata.csv`](../restricted_norgate/batch4c1_implementation_gap/strata.csv).

| Policy | Mean signed gap | Mean positive gap | Compliant S2 plans above decision budget at S4 | S4 exceedance persisting through S5, decision budget |
|:--|--:|--:|--:|--:|
| A | −0.78 | 6.55 | 29 of 154 compliant plans | 65 of 87 S4 exceedances |
| B | −0.51 | 5.96 | 60 of 229 | 39 of 60 |
| C | +0.06 | 7.31 | 57 of 229 | 34 of 57 |
| F | −0.77 | 5.95 | 64 of 229 | 32 of 64 |

Every B/C/F final S2 plan was within its own decision budget, yet approximately one quarter exceeded that budget at the next opening S4. Mean signed gaps are close to zero while mean positive parts remain around six to seven basis points, indicating that negative gaps offset positive gaps in the averages. The reported **mean** S2-to-S3 pre-fill changes are negative (A −4.59, B −3.41, C −4.04, F −3.77 bp), while the corresponding mean S3-to-S4 fill-stage changes are positive (A +3.81, B +2.90, C +4.10, F +3.00 bp). Those aggregate means offset; the available summary does not establish how frequently the two components have opposing signs on individual dates. The combined S2-to-S4 gap is therefore not properly labeled execution slippage. S4-to-S5 movements reflect subsequent closing valuation and NAV changes. All four policies have valid stages for each of the 229 decision/open pairs; the final calendar close has no invented following pair.

![Figure 2. Distribution of signed S4−S2 risk gaps, exposure basis points of NAV.](../restricted_norgate/batch4c1_implementation_gap/figure_gap_distribution.svg)

**Figure 2.** Distribution of signed S4−S2 gaps. The horizontal axis is modeled exposure basis points of NAV, not return or transaction-cost basis points. Source: original Batch 4B journals reconstructed in Batch 4C.1.

## 7. Economic Mechanisms

Figure 3 displays the date-by-date symmetric accounting decomposition defined in §5.3. It describes observed modeled-risk differences; its components are not estimated policy effects.

![Figure 3. Exact symmetric B−A modeled-risk decomposition, exposure basis points of NAV.](../restricted_norgate/batch4c3_economic_mechanisms/figure_exact_decomposition.svg)

**Figure 3.** Exact B−A risk decomposition. Each date's observed difference equals the two symmetric components, measured in exposure basis points of NAV. The initial shared all-cash close uses the explicit zero-component convention. Source: Batch 4C.3 original-journal reconstruction.

### 7.1 Capital use and portfolio composition

The average portfolio was largely in cash. Mean invested fractions were 33.31%, 33.48%, 38.36%, and 32.51% for A/B/C/F, respectively. B's average deployment exceeded A's by only 0.17 percentage points on matched closes, while B's mean modeled closing risk was lower. Thus B's lower average risk cannot be summarized as lower average capital deployment. The order journal records proposed buys and some sizing limits but not the complete qualifying-candidate funnel. A day without a proposed order cannot be classified as a day without signals. Composite buy rejection codes also prevent a unique allocation of idle cash to individual limits.

![Figure 4. Capital deployment paths by policy, invested assets divided by same-day NAV.](../restricted_norgate/batch4c2_capital_deployment/figure_deployment_paths.svg)

**Figure 4.** Capital deployment by policy. The vertical axis is invested assets divided by same-day NAV; all 230 closing dates are aligned and the first is the initial all-cash state. Source: Batch 4C.2 verified closing balances.

**Table 3. Portfolio composition and trading.** Means use 230 closes except position-weight concentration and \(Q\), which exclude the initial all-cash close. Source: Batch 4C.2 [`policy_aggregate.csv`](../restricted_norgate/batch4c2_capital_deployment/policy_aggregate.csv) and Batch 4C.3 [`policy_summary.csv`](../restricted_norgate/batch4c3_economic_mechanisms/policy_summary.csv).

| Policy | Mean holdings | Mean top position share of invested assets | Mean position HHI | Mean risk per invested dollar \(Q\) | Buys / sells | Modeled total cost |
|:--|--:|--:|--:|--:|--:|--:|
| A | 8.33 | 21.47% | 0.1581 | 11.72% | 143 / 140 | $8,238 |
| B | 9.27 | 20.66% | 0.1437 | 11.00% | 158 / 205 | $10,046 |
| C | 9.93 | 18.21% | 0.1296 | 10.86% | 173 / 211 | $10,915 |
| F | 9.21 | 20.86% | 0.1465 | 11.06% | 158 / 201 | $9,622 |

The exact symmetric B−A decomposition of mean modeled closing risk is **−19.92 basis points of NAV = +1.98 basis points from observed deployment difference −21.91 basis points from observed risk-per-invested difference**. It holds date by date, with maximum absolute residual approximately \(1.04\times10^{-17}\) exposure fraction. B also has about 0.95 more holdings on average and lower mean position-value HHI. These are composition descriptions; lower HHI by itself does not establish a diversification benefit, and the decomposition does not identify an overlay, security-selection, signal-mix, or stop-placement effect. All six policy-pair decompositions are archived, but none is a new inferential contrast.

### 7.2 Trading, costs, and simulated performance

B recorded 363 fills against A's 283, including 65 more sells and 15 more buys. B's gross traded notional was approximately $12.83 million against A's $10.82 million, and its modeled cumulative costs were $1,808 higher. Cost relative to the common $1 million initial NAV was 100.46 basis points for B and 82.38 for A; these are cumulative modeled-cost ratios, not daily returns. The approved fill-cost model is intentionally simple and does not estimate market impact, capacity or tax effects. A no-cost policy path was not simulated, so the observed NAV difference cannot be decomposed causally into trading-cost and risk-control effects.

B's simulated cumulative return was −4.84% versus A's −6.14%, a descriptive difference of +1.30 percentage points. B's maximum drawdown was −7.99% versus A's −9.22%. These outcomes are negative in absolute terms, and the study contains no separately justified return-superiority test. The contemporaneous Pearson correlation between the B−A closing risk difference and B−A same-day NAV return difference was +0.219 across 229 subsequent closes. Because both paths respond to the same historical market and diverging holdings, this co-movement is neither predictive evidence nor a risk-adjusted performance comparison.

## 8. Robustness

Temporal diagnostics retain the complete locked series while examining its concentration. June 2026 contributes −4.52 basis points of the full −11.27 basis point mean, approximately 40% of the signed estimate. The first and second 115-close means are −8.96 and −13.58 basis points. Each descriptive leave-one-month-out mean remains negative, ranging from −12.73 basis points when April is omitted to −7.43 when June is omitted. The largest single-day contrast is −125.22 basis points on 9 June 2026; omitting only that date would move the mean to approximately −10.77 basis points. These calculations diagnose influential episodes; they do not authorize exclusions or constitute independent replications.

Exploratory alternative common-reference thresholds of 3.5% and 4.5% yield B−A mean positive excesses of −14.95 and −5.09 basis points, respectively, from the same archived closing risks. These are **different estimands**, lack new inference, and do not replace the locked 4% comparison. Model sensitivity to alternative stop-gap buffers, execution costs, dividend dates or trading rules cannot be estimated from the archived paths without changing assumptions and conducting a new approved simulation. Such counterfactuals are unresolved rather than imputed.

![Figure 5. Monthly contributions to the locked B−A estimate, exposure basis points of NAV.](../restricted_norgate/batch4c4_robustness/figure_monthly_contributions.svg)

**Figure 5.** Monthly contributions to the locked B−A mean. Each monthly sum is divided by all 230 closes so the bars add to the full-period estimate; units are exposure basis points of NAV. Source: Batch 4C.4 reproduction of the official paired daily series.

## 9. Discussion

The historical result supports a narrow conclusion: within the approved model and fixed inspected calendar, B has lower average positive closing stop-gap excess above the common reference than A. Because B is designed to trim the same measure toward 4%, this direction has a partly mechanical explanation. The empirical content lies in the magnitude and persistence of the **closing** difference after execution and valuation, the presence of opening budget crossings despite compliant plans, and the accompanying capital and trading paths. The prespecified block-bootstrap interval lies below zero for the chosen block length, and two block-length sensitivities retain that direction. Reproduced bootstrap bytes verify the numerical procedure; they do not prove that its stationarity assumptions hold or that the window supplies independent confirmation. June 2026 contributes roughly 40% of the signed estimate, making transportability especially uncertain.

The mechanism studies refine the result without turning it into a causal finding. Decision-time compliance did not guarantee next-open compliance, while B's lower average risk coexisted with slightly higher deployment, more positions, more fills, higher modeled costs, and a less negative simulated return. The exact deployment/\(Q\) split shows that the observed risk difference is primarily associated with risk per invested dollar in an accounting sense. It does not say whether B's overlay, the resulting security mix, timing, or another path-dependent interaction produced that difference. The incomplete candidate archive and composite rejection reasons further limit explanations for persistent cash.

## 10. Limitations

First, the sample has only 230 sessions and was previously inspected during research development. Point-in-time membership and frozen code improve within-study consistency but do not make the window out-of-sample or remove selection concerns. Circular block bootstrap assumes sufficiently stable dependence; wrapping endpoint blocks and the small number of effective blocks at length 40 are material limitations. The reported interval is not a p-value and cannot establish external or causal superiority.

Second, marked stop-gap exposure is a model-specific accounting proxy. It measures marked price distance above adjusted stops plus a fixed buffer; it is **not** the realized downside of the account, a loss probability, value at risk, expected shortfall, a stop-fill guarantee, or a drawdown limit. No independent calibration relates its level or changes to subsequent tail losses in this study. It depends on raw marks, adjusted stops, the 1% gap allowance and NAV. The threshold alternatives illustrate sensitivity of the descriptive contrast but cannot validate the proxy against realized tail loss. Dynamic-budget C and fixed F are secondary paths with different permitted exposures, so their raw 4% excesses should not be read as policy failures under their own budgets.

Third, modeled execution assumes raw next-open fills with fixed adverse slippage and commission, whole orders, **no order-size-dependent market-impact model**, no intraday stops, no taxes and no cash interest. This rules out a realistic assessment of liquidity stress and capacity. The journal does not retain the complete candidate-level signal funnel or uniquely disaggregate composite buy-rejection reasons; idle cash and policy composition therefore cannot be causally attributed to a single constraint. Corporate-action and payment handling follow approved source-precision judgments; alternative treatment was not tested. The acquired data vintage, constituent definition and licensing conditions constrain external reproducibility. All four simulated cumulative returns are negative, and no live-trading inference follows from their ranking.

Fourth, the exact deployment/\(Q\) decomposition is an identity for the **observed** portfolios, not an intervention on deployment with composition fixed. It cannot identify how much of B's difference came from the overlay, entry opportunities, stop placement or later path dependence. No matched causal counterfactual or independently calibrated downside outcome is available.

Fifth, provenance has one unresolved exception: the Batch 4C.1 reproducibility manifest's hash for its `independent_validation.json` does not match that file's current bytes. The mismatch has been disclosed in Batch 4C.2–4C.4 and is not silently treated as resolved. That JSON was not used for numerical manuscript claims; the underlying original Batch 4B hashes and used Batch 4C tables passed the subsequent checks. A proposed versioned correction is documented separately for researcher review and would preserve all first-run files.

## 11. Conclusion

An audited, staged historical simulation shows that a final risk plan and its executed portfolio can differ, and that lower closing modeled risk need not coincide with lower average capital deployment. Over the approved 230-session window, B's mean positive stop-gap excess above a common 4% reference is 11.27 basis points of NAV below A's, with a prespecified block-bootstrap interval below zero under the modeled historical design. The direction is partly expected from B's risk rule; the study's contribution is the measured implementation path and its accounting and identification limits. The result is temporally concentrated, all policy returns are negative, and neither the interval nor the exact accounting comparisons identifies future downside protection or causal mechanisms. The manuscript supports a qualified historical description while leaving external validity and several economically important counterfactuals unresolved.

## Reproducibility and Data Availability

The approved protocol, code identities, original journal hashes, official Batch 4B summary, and Batch 4C analysis/validation scripts establish an internal audit trail. The restricted original Norgate extraction, security-level journals, and private empirical artifacts cannot be redistributed or placed in a public repository under the project's licensing restrictions. A lawful replication would require an independently licensed data source and the approved versioned code and protocol; equality of vendor acquisition vintage, universe membership and corporate-action terms could not be assumed. Aggregate tables and figures in this internal draft reference private artifacts and require a separate disclosure and licensing review before public release. No new strategy simulation was performed for Manuscript V4.1.

## References

Almgren, R., and Chriss, N. (2001). “Optimal execution of portfolio transactions.” *The Journal of Risk*. DOI: [10.21314/JOR.2001.041](https://doi.org/10.21314/JOR.2001.041). Volume, issue and page range require a final publisher-catalogue check; no page metadata is asserted here.

Bailey, D. H., Borwein, J. M., López de Prado, M., and Zhu, Q. J. (2017). “The probability of backtest overfitting.” *The Journal of Computational Finance*, 20(4). [Publisher article](https://www.risk.net/journal-of-computational-finance/2471206/the-probability-of-backtest-overfitting). DOI: [10.21314/jcf.2016.322](https://doi.org/10.21314/jcf.2016.322). Page range unresolved in the accessible publisher record; verify before submission.

Brown, S. J., Goetzmann, W., Ibbotson, R. G., and Ross, S. A. (1992). “Survivorship bias in performance studies.” *The Review of Financial Studies*, 5(4), 553–580. DOI: [10.1093/rfs/5.4.553](https://doi.org/10.1093/rfs/5.4.553).

Jegadeesh, N., and Titman, S. (1993). “Returns to buying winners and selling losers: Implications for stock market efficiency.” *The Journal of Finance*, 48(1), 65–91. DOI: [10.1111/j.1540-6261.1993.tb04702.x](https://doi.org/10.1111/j.1540-6261.1993.tb04702.x).

Kaminski, K. M., and Lo, A. W. (2014). “When do stop-loss rules stop losses?” *Journal of Financial Markets*, 18, 234–254. DOI: [10.1016/j.finmar.2013.07.001](https://doi.org/10.1016/j.finmar.2013.07.001). Publication details verified against the [MIT institutional record](https://dspace.mit.edu/entities/publication/bb69ca4b-0cdc-487f-831d-63b2e84fafee).

Künsch, H. R. (1989). “The jackknife and the bootstrap for general stationary observations.” *The Annals of Statistics*, 17(3), 1217–1241. DOI: [10.1214/aos/1176347265](https://doi.org/10.1214/aos/1176347265).

Moreira, A., and Muir, T. (2017). “Volatility-managed portfolios.” *The Journal of Finance*, 72(4), 1611–1644. DOI: [10.1111/jofi.12513](https://doi.org/10.1111/jofi.12513).

Moskowitz, T. J., Ooi, Y. H., and Pedersen, L. H. (2012). “Time series momentum.” *Journal of Financial Economics*, 104(2), 228–250. DOI: [10.1016/j.jfineco.2011.11.003](https://doi.org/10.1016/j.jfineco.2011.11.003).

Novy-Marx, R., and Velikov, M. (2016). “A taxonomy of anomalies and their trading costs.” *The Review of Financial Studies*, 29(1), 104–147. DOI: [10.1093/rfs/hhv063](https://doi.org/10.1093/rfs/hhv063).

Politis, D. N., and Romano, J. P. (1992). “A circular block-resampling procedure for stationary data.” In R. LePage and L. Billard (eds.), *Exploring the Limits of Bootstrap*. Wiley. [Stanford technical report record](https://statistics.stanford.edu/technical-reports/circular-block-resampling-procedure-stationary-data). Chapter page range unresolved; verify the edited-volume record before submission.

Richard, J.-C., and Roncalli, T. (2019). “Constrained risk budgeting portfolios: Theory, algorithms, applications & puzzles.” [arXiv preprint 1902.05710](https://arxiv.org/abs/1902.05710). Journal publication status not verified.

Roncalli, T. (2014). *Introduction to Risk Parity and Budgeting*. [arXiv version 1403.1889](https://arxiv.org/abs/1403.1889). This citation refers to the accessible manuscript version; book edition details require review if substituted.

White, H. (2000). “A reality check for data snooping.” *Econometrica*, 68(5), 1097–1126. DOI: [10.1111/1468-0262.00152](https://doi.org/10.1111/1468-0262.00152).
