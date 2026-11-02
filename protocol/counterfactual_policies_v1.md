# Counterfactual Portfolio Policies V1

Status: EXPLORATORY_PROTOCOL
Established: 2026-11-01

## Common assumptions

- Historical daily US equity prices.
- Existing validated MPB entry signals.
- Original MPB stop, EMA21, 3R/5R exit priorities.
- T-close decisions, hypothetical T+1 opening fills.
- $10 commission per fill; 5bps adverse slippage.
- Integer shares, no leverage.
- Same-auction sell proceeds are not used to fund buys.
- Unverified corporate actions block simulation.
- Original frozen FMA engine is never modified.

## Policy A

Baseline MPB integration with original 4% new-risk
planning budget and no additional portfolio-risk trim.

Observed risk may exceed 4% after price changes.

## Policy B

Fixed 4% mark-to-stop portfolio risk target.

At T close, calculate incumbent risk using known prices.
After accounting for already planned MPB sell orders,
schedule additional reductions if exposure exceeds 4%.

Select positions in descending order of their remaining
planned risk contribution, ticker as deterministic tie-break.

Use the minimum integer shares needed to reach the
target at T-close prices. Execute no earlier than T+1.

No expectation of guaranteed T+1 compliance.

## Policy C

Volatility-conditioned risk target:

budget_t = 0.04 * clip(sigma_ref / sigma_t20, 0.5, 1.25)

sigma_t20: sample standard deviation of the latest
20 SPY adjusted close-to-close returns, annualized.
sigma_ref: median 20-return realized volatility from
2025-01-02 through 2025-08-29, using only that period.

Same additional trim policy as B.

C may permit a larger risk budget than 4%; comparisons
must report both exposure and risk-adjusted outcomes.

## Common research caveats

The underlying universe uses contemporary constituents.
Past research has already inspected the historical period;
results are exploratory and not independent out-of-sample.

The original frozen strategy remains unchanged. The
historical execution layer is a research approximation.

Do not interpret account consistency as economic alpha.
Do not tune policy settings after observing results without
recording a new experiment version.
