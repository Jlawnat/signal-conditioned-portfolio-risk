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
