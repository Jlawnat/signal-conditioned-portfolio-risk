# Planned Risk Budgets and Executed Exposure in a Signal-Driven Equity Portfolio

*Manuscript V3 working draft · pre-empirical sections · 2026-11-02*  
*NG-SF-270-LW is a proposed, unfrozen historical robustness experiment. No V3 A/B/C results exist.*

## Abstract — results pending

Portfolio risk budgets are set at decision time, while the portfolio they govern is formed through subsequent orders, opening prices and corporate actions. We propose to compare a momentum–pullback–breakout research baseline with fixed and volatility-conditioned stop-gap overlays in a sector-free, Norgate-defined historical universe. A 270-aligned-bar signal requirement fixes the eligible study window to 2 December 2025 through 30 October 2026. Decision-time planned positions and next-open simulated positions will be archived separately. The primary proposed comparison concerns positive exposure above a common 4% reference; implementation gaps, trading costs, deployment and NAV are secondary or mechanistic outcomes. The experiment has not been run. The window was already inspected in earlier work, so any future estimates from it will remain exploratory.

## 1. Introduction

A portfolio risk rule can appear satisfied when orders are planned and be exceeded once the orders execute. Between the two observations, prices may move, accepted orders may be rejected at the open, trading costs reduce NAV, and corporate actions may change share and stop units. In a signal-driven portfolio, a risk overlay can also alter which positions remain available for later opportunities. These pathways make a decision-time target and a realized portfolio path distinct objects of study.

This paper studies a marked stop-gap exposure measure within a specified momentum–pullback–breakout (MPB) research integration. The measure adds each holding's marked distance above its adjusted initial stop and a one-percent gap allowance. It supports transparent share-level accounting, while remaining a proxy rather than a probability of loss, a stop guarantee, or a drawdown limit. Our proposed contribution is a reproducible account of how a planned budget relates to the exposure observed immediately after simulated execution and to subsequent portfolio paths. We do not assume that a tighter exposure target improves returns.

The original V4 and V5-U simulations are useful exploratory evidence, but they used a current-constituent universe, incomplete action verification and a reconstructed timing sample. Their results remain in Manuscript V2 and are not reclassified as decision-time evidence here. A new event journal can retain the complete accepted plan before T+1 information and link it to the fill record. The proposed Norgate-only experiment replaces the retrospective universe with Norgate daily constituents and applies a sector-free rule to all policies. It is a named research variant, not a replication of every frozen FMA order or its 24% sector constraint.

The acquired trial begins too late for the original first session to meet the frozen 270-bar stock/SPY requirement. We retain that requirement and start at the first eligible SPY decision date, 2 December 2025. This availability-based choice precedes any new portfolio simulation. It leaves 230 sessions and at most 229 decision/open pairs through 30 October 2026. The interval has already been examined in the project's development, so the later-window experiment is a historical robustness study rather than independent confirmation.

## 2. Related literature and scope

Risk-budgeting work emphasizes allocation under explicit risk definitions and constraints (Roncalli, 2014; Richard and Roncalli, 2019). Our marked stop-gap sum differs from portfolio variance contributions: it can increase when a holding appreciates while its initial stop remains fixed. This property motivates the overlay but does not establish that the overlay improves a probabilistic risk measure.

Moreira and Muir (2017) study volatility-managed factor exposure. Our dynamic policy uses lagged SPY volatility to change a stop-gap target, so their results supply motivation for a state-dependent rule rather than evidence of its performance here. Cross-sectional momentum research (Jegadeesh and Titman, 1993) and time-series momentum research (Moskowitz, Ooi and Pedersen, 2012) provide context for trend-based signals; the MPB entry filter and its executable portfolio path are specific to this implementation.

Trading costs can materially change anomaly returns (Novy-Marx and Velikov, 2016). Survivor-conditioned samples can bias historical comparisons (Brown et al., 1992), and repeated inspection raises overfitting concerns (Bailey et al., 2017). These considerations motivate point-in-time membership, a fixed calendar, cost accounting and explicit separation of exploratory from future confirmation evidence. The present design does not claim to correct all historical-vintage or data-license limitations.

## 3. Risk framework and hypotheses

For position \(i\) at event state \(s\), let \(q_{i,s}\) be raw shares, \(P_{i,s}\) the raw mark, \(S_{i,s}\) the action-adjusted stop in raw share units, and \(NAV_s\) cash plus receivables plus marked holdings. Define

\[
R_s=\frac{\sum_i q_{i,s}\left[\max(0,P_{i,s}-S_{i,s})+0.01P_{i,s}\right]}{NAV_s}.
\]

The numerator measures marked capital between price and stop plus a fixed gap allowance. A price rise can increase this contribution when the stop does not rise with it. A stop may also fail to execute at its reference price. Consequently, \(R_s\) is neither VaR nor expected shortfall and does not bound realized maximum drawdown.

At T close, S0 records current holdings, S1 records MPB exits plus any overlay reductions, and S2 records the complete accepted plan including buys. At T+1 open, S3 is after documented overnight actions but before fills; S4 is after fills and costs. S5 marks the next close. The proposed implementation gap is \(G_T=R_{S4,T+1}-R_{S2,T}\), with positive part \(\max(G_T,0)\). A planned-compliant-to-opening-exceedance event requires \(R_{S2,T}\le b_T+\epsilon\) and \(R_{S4,T+1}>b_T+\epsilon\), where \(b_T\) is the decision-time budget and \(\epsilon=10^{-9}\) in exposure-fraction units. These are descriptive changes across event states. They do not isolate slippage or identify a causal effect without a prespecified counterfactual.

The proposed primary historical contrast is Policy B minus Policy A in mean positive **end-of-day** exceedance above a common 4% reference. A has no mandatory incumbent overlay, so its common-reference exceedance is not an own-overlay compliance failure. We hypothesize that B's additional reductions may lower this exposure statistic, without predicting lower drawdown or higher NAV. We separately expect some T-close plans to differ from next-open exposure. Policy C is a secondary dynamic-budget comparison; its own 2%–5% budget and the common 4% reference must be reported separately. The proposed fixed comparator F uses B's trim rule at the mean C budget calibrated from 165 pre-study SPY volatility observations, 3.8654080953% in the acquired extract. F is a mechanism comparison, not a new primary policy or a causal identification strategy; its inclusion awaits protocol approval.

## 4. Proposed data and methods

The proposed universe is Norgate's daily S&P 500 constituent definition, including observed former members. The experiment starts with $1 million cash and no holdings at the 2 December 2025 close. A stock remains a member when it lacks enough signal history; it simply cannot produce a signal until it has 270 valid dates exactly aligned with SPY through T. No bar is padded or drawn from after T. The acquired Norgate trial supplies four adjustment views, but only NONE raw prices enter simulated fills and NAV. TOTALRETURN OHLC is normalized to raw T units using the same-date close ratio; CAPITAL volume is normalized to T raw-share units under an explicitly checked reciprocal price-volume convention. Frozen technical predicates use normalized signal bars, while minimum price and preceding-20-session liquidity gates use raw economic units. This is a documented transformation and cannot be described as unchanged frozen FMA input behavior.

Policy A retains the baseline MPB exit and new-order planning rules without an incumbent overlay. Policy B adds a fixed 4% marked stop-gap trim after MPB exits. Policy C uses the same trim procedure with a trailing-SPY-volatility target bounded from 2% to 5%. The sector-free variant removes the 24% sector cap and Unknown-sector rejection identically for all policies. Candidate rank, share sizing, position limits, signal thresholds and no-credit-for-pending-sell planning semantics otherwise follow the independent research executor. The original frozen FMA source, V4/V5-U outputs and manuscripts remain separate reference artifacts.

The proposed executor decides at T close and hypothetically fills at T+1 raw open, applying five basis points of adverse slippage and a $10 commission per fill. Sells precede buys; sell proceeds from the same opening auction do not fund buys. Positions use integer shares. The model omits partial fills, intraday stop execution, taxes, market impact and cash interest. Complete decision plans, opening rejections and fills must reconcile by deterministic order ID. S2 uses T-close NAV as denominator and reports estimated costs separately; S4 uses actual post-cost NAV. This denominator convention awaits protocol approval.

Corporate-action accounting must use verified raw-share terms. Dividends accrue to a separate receivable only for prior-close entitled shares and become spendable on documented payment dates. Verified splits change raw quantities, cost and stop units once, including pending orders. A cash-only terminal event requires documented consideration and payment timing. Unverified material terms, fractional-share treatment and successor-share conversions block the affected path rather than receiving invented values. A private possible-signal screen ranks verification work; it does not establish actual holdings or permit post-hoc security exclusion.

The proposed primary statistic is the 230-date mean of the paired B minus A daily positive exposure excess above 4%, including valid no-order days. The proposed implementation-gap analysis uses S4 exposure minus the archived S2 exposure, with the T decision budget for opening exceedance classification and at most 229 valid pairs. A missing mark or material action term blocks the full-window primary estimate; no date or security is silently dropped. The draft protocol proposes a 95% circular moving-block bootstrap interval for the primary paired series, using 20-session blocks, 10,000 replicates and a fixed seed, with 10- and 40-session block sensitivities. It proposes no confirmatory p-value or secondary significance tests. The interval would remain exploratory because the policy paths are serially dependent and the period was previously inspected. The comparator, uncertainty and exception rules require dated researcher approval before the official simulation.

## 5. Results and discussion — pending

No NG-SF-270-LW policy simulation has been run. Add policy paths, decision/open gaps, action reconciliation, cost and NAV results only after a dated protocol approval and the material accounting and implementation gates pass. Report null or adverse outcomes with the same prominence as favorable ones. Keep the original 282-session V4/V5-U findings labeled exploratory and outside the V3 experiment's primary comparison.

## References

Bibliographic records are retained in [the V2 reference file](references_v2.bib). Final V3 reference and source verification remains an editorial task.
