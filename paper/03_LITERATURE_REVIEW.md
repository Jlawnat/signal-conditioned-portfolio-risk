## 2. Related literature

### 2.1 Risk budgets and constraints

Risk budgeting seeks to make allocation decisions in units of risk rather than capital alone. Roncalli's [2014 manuscript](https://arxiv.org/abs/1403.1889v1) provides a broad framework, and Richard and Roncalli's [2019 preprint](https://arxiv.org/abs/1902.05710v1) shows that weight constraints and turnover alter the constrained risk-budgeting problem. The present overlay is deliberately narrower: it trims integer shares against a stop-gap dollar target after planned MPB exits. Its results do not test the optimality of equal risk contributions or the theory of variance-based risk parity.

### 2.2 Dynamic exposure and momentum

Moreira and Muir [2017](https://onlinelibrary.wiley.com/doi/10.1111/jofi.12513) study volatility-managed factor portfolios. Policy C uses lagged SPY volatility to vary a stop-gap risk target, but the prior factor results do not predict the outcome of this equity strategy. Momentum studies motivate inspection of the signal pool: Jegadeesh and Titman [1993](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1993.tb04702.x) examine cross-sectional stock winners and losers, and Moskowitz, Ooi and Pedersen [2012](https://doi.org/10.1016/j.jfineco.2011.11.003) study time-series momentum in futures. MPB adds pullback and breakout conditions; its executed entries constitute a selected subset of historical candidates. Direct literature identifying the specific signal-scarcity/cash interaction in this implementation remains [CITATION NEEDED].

### 2.3 Implementation and backtest reliability

Transaction frequency matters because a rule that improves a risk metric may consume more capital in commissions and slippage. Novy-Marx and Velikov [2016](https://academic.oup.com/rfs/article-abstract/29/1/104/1844518) document trading-cost sensitivity across anomaly portfolios; this study reports modeled costs but does not assume they exhaust real implementation frictions. Brown, Goetzmann, Ibbotson and Ross [1992](https://academic.oup.com/rfs/article-abstract/5/4/553/1590264) show that survivor-conditioned samples can distort apparent performance relations. Bailey and coauthors' [2015 author-hosted manuscript](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) studies backtest overfitting. Those works support explicit treatment of current-constituent selection and prior inspection of the 282-session window, without providing a quantitative correction for either bias here.

This paper contributes a documented comparison of three fixed implementations and separates a capped planning regime from a cap-neutral research sensitivity. It reports planned-risk exposure, observed constraint exceedances, deployment and realized NAV together. The contribution is a bounded empirical account of one strategy integration, with no claim that its combination of rules is novel in the broader literature.
