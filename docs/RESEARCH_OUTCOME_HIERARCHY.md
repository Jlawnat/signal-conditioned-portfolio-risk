# Proposed research outcome hierarchy

Status: **proposal for researcher approval**, written after inspection of the 282-session historical results. It is not a preregistered hierarchy and does not redefine A, B or C.

## Implemented and observable facts

The V5-U daily files contain date, NAV, cash, dividend receivable, holdings, daily P&L components, execution cost and policy budget. Fills and prices are in the trade files. The independent constraint audit reconstructs end-of-day mark-to-stop risk, sector weight, position weight and holdings from fills and local price panels. The comparison report supplies cumulative return, realized drawdown, mean invested fraction, mean cash fraction, volatility, zero-risk-free Sharpe and cumulative execution costs. Policy A uses a 4% new-risk planning budget without incumbent trimming; B targets 4% after planned MPB exits; C targets 2%–5% using trailing SPY volatility. The end-of-day risk paths for V5-U require reconstruction from the source panels and trades; the summary JSON contains counts and extrema, not all daily risk observations.

## Proposed primary outcomes

1. End-of-day planned stop-gap risk as a fraction of NAV: `sum_i shares_i × [max(0, close_i − stop_i) + 0.01 × close_i] / NAV`. Report mean, maximum and daily path. This is an exposure proxy, not VaR, expected shortfall, realized loss or maximum drawdown.
2. Days and magnitude above each policy's **own** budget. Report the fraction of 282 sessions and maximum exceedance in percentage points. The budget is a planning target; a breach is an observed end-of-day condition.
3. Days above the **common fixed 4% reference** for all policies. C's own budget can exceed 4%, so this is a distinct comparison, not a compliance test of C's own rule.

## Proposed secondary outcomes

Mean invested fraction and cash exposure (the receivable share explains why these need not sum to exactly 100%); maximum drawdown of NAV; trade count and modeled execution cost; and days above the 24% sector, 10% name, and 14-holding reference limits. These are observable or in existing reports. "Capital deployment efficiency" has no unique direct metric: if used, define it as a descriptive relation between invested fraction, signal availability and net outcome, without claiming optimality.

## Exploratory and post-hoc outcomes

Cumulative NAV performance is observed but economically conditional on dividend and execution assumptions. Policy A's 158 entries, 151 completed lifecycles, 31.126% completed win rate and 0.5563 completed profit factor are stored in `audit/p3_v5u_A_trade_lifecycles.json`; those were inspected after simulation and are not independent signal-quality tests. Entry forward returns and month-cluster bootstrap diagnostics are exploratory; executed entries are selected and horizons may overlap. Actual FMA StockTrak account attribution is supplementary and does not identify MPB-only returns.

## Researcher decision and interpretation

Approve or amend the primary ordering, treatment of C's common threshold, whether V5-U is the main regime and V4 a sensitivity, and the presentation of dividend-conditioned NAV. Record any amendment as a new dated protocol version. The current hierarchy can organize Draft V1 while marked post-hoc. No p-value or causal superiority claim follows from it.
