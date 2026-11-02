# Research protocol V1

Status: implementation description plus proposed paper analysis. Researcher approval is required for the proposed estimands and final manuscript framing; this document does not alter the frozen FMA source or historical outputs.

## Questions and hypotheses

**Proposed questions.** How do fixed and volatility-conditioned risk budgets change capital deployment, end-of-day constraint breaches, turnover costs, and risk–return outcomes relative to the baseline? How much of any observed difference coincides with signal scarcity and the transaction-cap regime?

**Proposed directional hypotheses, not findings.** H1: adding a fixed portfolio trim reduces days above its own 4% mark-to-stop budget. H2: a volatility-conditioned budget changes deployment and own-budget breaches relative to fixed budgeting. H3: any benefit in constraint control can be offset by turnover costs and path-dependent foregone gains. These are descriptive counterfactual hypotheses for a previously inspected sample, not pre-registered confirmatory tests.

## Confirmed implementation facts

The 282-session window is 2025-09-18 through 2026-10-30, with a $1,000,000 starting NAV. Signals are selected from the existing historical candidate CSV, sorted by descending score and ticker. Frozen FMA code provides technical features read-only, with source hashes checked at runtime. Decisions use information through T close; orders fill hypothetically at T+1 open. Buy fills pay 5 bps adverse slippage and $10 commission; sells receive 5 bps adverse slippage and pay $10. Shares are integers; cash cannot be negative; same-opening sell proceeds cannot fund buys. No partial fills, intraday stop execution, leverage, tax, or integrated cash interest is modeled. Dividend entitlement and receivables enter NAV; provider-only events can remain unsettled receivables. The research executor's stop adjustment on ex-date is an assumption.

**A:** Existing MPB exits and research entry integration, 4% *new-order planning* risk budget, with no extra incumbent portfolio-risk trim. Observed risk can exceed 4%.

**B:** Same MPB exits and signal pool, fixed 4% mark-to-stop portfolio target. At T close, after planned MPB sells, the overlay sorts remaining positions by descending risk contribution and ticker, then plans minimum integer-share reductions for T+1. The target is assessed at T-close prices; T+1 and later risk may exceed it.

**C:** Same as B, with `budget_t = 0.04 × clip(sigma_ref / sigma_20,t, 0.5, 1.25)`, hence 2%–5%. `sigma_20,t` is sample standard deviation of the latest 20 adjusted SPY close-to-close returns, annualized by `sqrt(252)`. `sigma_ref` is the median 20-return volatility during 2025-01-02–2025-08-29; the stored V5-U C summary reports `0.14485424053056145`. The volatility observation at T is used only for T-close decisions. C can legitimately exceed a fixed 4% benchmark.

For all policies, planner risk per held share is `max(0, close_raw - adjusted_initial_stop) + gap_buffer × close_raw`; `gap_buffer` is 1%. Entry sizing also accounts for adverse slippage and two commissions. Position, sector, volume, cash and 14-holding constraints are checked in the research planner. End-of-day audits observe realized holdings and may find drift beyond planning limits.

**V4:** Contest-capped research scenario. The runner checks `CONTEST.transaction_limit - STRAT.reserve_transactions = 400 - 40 = 360` during overlay/new-buy planning. It is not a faithful 282-day contest replay: the contest calendar is shorter and the planner differs from the original order generator. V4 B/C ended with 370/373 simulated fills, so `360` must not be described as a hard realized-fill ceiling.

**V5-U:** Transaction-cap-neutral research scenario with a nonbinding `1,000,000,000` threshold. A/B/C had 313/464/478 fills. These are separate policy paths; V4 B/C figures cannot be mixed with V5-U B/C. The shared A output does not make the scenarios interchangeable.

## Outcomes and interpretation

**Proposed primary descriptive outcomes:** mean invested capital/NAV; days above each policy's own end-of-day risk budget and magnitude of excess; terminal NAV/total return; maximum NAV drawdown. Report all four together and give the fixed 4% breach count separately for C. Risk budget is a stop-based exposure planning measure; maximum drawdown is a realized path statistic. Neither is a guarantee against gap losses. A portfolio can meet a risk target at T close and exceed it after the next opening or market drift.

**Proposed secondary outcomes:** annualized daily NAV volatility, zero-risk-free descriptive Sharpe (explicit convention), transaction count, commissions plus slippage, sector/position/holdings breaches, cash share, provisional dividend receivables, and paired daily contribution diagnostics. Paired comparisons remain descriptive because policies create different future positions and selection paths. No statistical significance claim is authorized from the current artifacts.

## Limits and reproducibility

The universe uses current S&P 500 constituents rather than point-in-time membership, creating survivorship and selection bias. Adjusted historical prices and provider action records have potential revision and event-timing issues. Some dividends are inferred from provider records without independently verified payment dates; splits are unmodeled where encountered. Signal candidates were generated and this historical span inspected before this protocol. It is **in-sample exploratory evidence**, never out-of-sample. The reference signal/order pipeline is not fully certified against the research executor. Hypothetical next-open fills and fixed costs exclude liquidity impact, borrow, tax, and partial fills. The StockTrak reconciliation is supplementary and does not establish MPB-only returns or causal effects.

Reproduction requires the exact frozen-source hashes in `configs/mpb_exit_reference.json`; the signal CSV, raw/adjusted market bundle and manifest at their documented local paths; the dividend register; code revision; Python/dependency versions; and immutable output hashes. Reconcile per-policy daily and trade rows, NAV identities, source hashes, and V4/V5-U labels before computing figures. A future portable data manifest and environment lock are **MISSING**. Do not rerun 282 sessions merely to restate existing figures; first address a concrete defect.

## Decisions proposed for researcher approval

Approve the primary outcome ordering and whether V5-U is the main paper scenario with V4 as a sensitivity/constraint case; approve how prominently provisional dividend NAVs appear; approve a bounded signal/order parity sample design and a data-quality sensitivity analysis before final economic conclusions. Freeze any future amendments with a new protocol version and retain this one. No parameter tuning is proposed.
