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
