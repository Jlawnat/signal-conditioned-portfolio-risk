# Publication Research Protocol V2

**Project:** Independent Quantitative Finance Research  
**Status:** Draft for Researcher Review — Not Yet Frozen  
**Research type:** Computational and empirical portfolio research  
**Target:** Peer-reviewed quantitative finance / investment research journal

## 1. Proposed Paper Title

**From Planned Stop-Gap Risk Budgets to Realized Portfolio Risk: Execution Timing, Portfolio Constraints, and Capital Deployment**

中文：从计划止损风险预算到实际组合风险：交易执行时点、投资组合约束与资金部署。

该标题强调的是风险预算的实际实施，而不是暗示我们已发明了某种由交易信号直接决定的风险预算模型。

## 2. Central Research Question

**How do portfolio-level stop-gap risk-budget overlays translate into observed exposure control and realized portfolio outcomes when trading signals, execution delays, and position constraints interact?**

核心研究问题：

在一个由交易信号驱动的股票策略中，组合风险预算是否能够有效约束实际持仓风险？交易执行时滞、价格跳空、现有持仓以及资金约束如何影响最终结果？

论文希望区别三个层面：

- **Planned risk:** 在交易决策时点计算和计划控制的风险。
- **Executed exposure:** 订单实际模拟成交后形成的组合风险暴露。
- **Realized outcomes:** 后续真实价格路径下的净值变化、回撤和执行成本。

研究不以证明某个政策获得最高收益为目标。

## 3. Proposed Scientific Contributions

### Contribution 1 — Risk-budget implementation gap

研究计划风险预算与实际成交后风险暴露之间的差距，尤其是下一交易日开盘价变化可能使已经计划降至目标以内的组合再次超出预算。

预期贡献：建立可复现的计划—执行—收盘风险测量框架。

### Contribution 2 — Economic interpretation of stop-gap risk

研究以当前股价到初始止损价距离计算的组合风险，如何同时反映本金潜在损失和浮动利润回吐。

预期贡献：解释这种风险代理指标为什么可能促使组合削减上涨持仓，以及它与传统方差风险预算之间的差异。

### Contribution 3 — Risk constraints and portfolio path dependence

研究固定及动态风险覆盖规则如何改变持仓、现金利用、交易次数和执行成本。

预期贡献：在统一交易执行环境中揭示计划风险约束与实际组合结果之间可能存在的权衡。

上述三项均为拟检验贡献，不是已经证实的原创发现。

## 4. Hypotheses

### H1 — Fixed-budget exposure control

相对于没有额外持仓减仓覆盖规则的基准 A，固定预算覆盖政策 B 预计降低组合超过统一 4% stop-gap 风险参考值的平均超出幅度。

这是关于**定义明确的风险代理指标**的假设，不是关于最大回撤必然下降的假设。

### H2 — Execution-timing gap

收盘时计划的风险减仓，不必然等同于次日开盘成交后的风险暴露。

研究将检验计划后暴露、成交后暴露和随后收盘暴露之间的差异及其分布。

我们不预设每次开盘差异的方向均相同。

### H3 — Unrealized-profit giveback mechanism

当初始止损价保持不变时，持仓上涨可能增加按市值计算的 stop-gap 风险贡献，从而增加风险覆盖政策触发减仓的可能性。

需要通过订单原因、浮盈状态和风险贡献变化进行验证。不能仅从总交易次数推断该机制成立。

### H4 — Dynamic-budget trade-off

波动率条件化预算 C 可能改变资本投入、风险暴露和交易路径，但不预设其收益或最大回撤优于固定预算 B。

C 的自身预算超标与统一 4% 超标必须分别比较。

## 5. Experimental Policies

| Policy | Definition | Role |
|---|---|---|
| A — Baseline | 现有 MPB 策略与新增订单规划限制，不额外强制削减现有持仓 | 基准 |
| B — Fixed Overlay | 对现有持仓增加固定 4% stop-gap 风险预算覆盖规则 | 主要研究干预 |
| C — Dynamic Overlay | 使用 SPY 过去波动率调整 2%–5% 的预算覆盖规则 | 动态政策比较 |

三种政策必须使用相同的信号、行情、数据资格规则、订单执行环境和成本模型，区别只能来自明确记录的政策规则及其后续路径影响。

现有 V5-U 的执行器是独立研究环境；不能未经验证就称其为冻结 FMA 交易执行器的精确复制。

应另外考虑一项事前固定风险水平的机制对照，用于辨别 C 的结果是否来自预算变化本身，而不只是其平均预算水平不同。该对照的必要性和参数确定方式需在正式实验前批准。

## 6. Main Risk Measure

保留现有研究使用的指标：

\[
R_t =
\frac{
\sum_i q_{i,t}
\left[
\max(0,P_{i,t}-S_{i,t})
+0.01P_{i,t}
\right]
}{
NAV_t
}
\]

其中 \(P_{i,t}\) 为持仓当前价格，\(S_{i,t}\) 为研究执行器记录的调整后初始止损价格。

该指标定义为 **Marked Stop-Gap Exposure**。

它不是 VaR、Expected Shortfall、未来收益预测，亦不构成实际损失上限。

## 7. Primary and Secondary Outcomes

### Primary candidate estimand

建议将相对于统一 4% 风险参考值的平均超出幅度，作为未来确认性研究的单一主要指标：

\[
E_{4\%}=
\frac{1}{T}
\sum_{t=1}^{T}\max(R_t-0.04,0)
\]

该指标同时反映超标频率和幅度，避免只统计超标天数却忽略严重程度。

主要对照为 B 与 A 的 \(E_{4\%}\) 差异；C 的共同阈值结果作为预先声明的次要比较。

### Secondary outcomes

- 超过统一 4% 风险参考值的天数比例
- 超过政策自身预算的天数比例和超出幅度
- 风险超标持续时间
- 计划减仓与实际成交后风险差异
- 平均资本投入比例
- 最大回撤、累计收益及波动率
- 交易次数、换手率及执行成本
- 行业与个股集中度

“资本部署效率”暂不作为已经识别的指标。若以后提出效率指标，必须明确经济定义和解释边界。

## 8. Data Design

### Data source

优先使用已接入的 Norgate Platinum 数据，研究历史 S&P 500 成分、日度行情和退市证券。

### Required safeguards

- 历史成员资格按交易日期及生效时点判定。
- 未取得足够 126 个历史价格观测的证券，不允许计算需要完整预热期的信号，但不能因此将其从历史成员记录中删除。
- 使用一致且明确的原始价格、资本调整价格和股息现金处理规则。
- 核实拆股、退市、收购及关键股息事件。
- 历史行业分类缺失时，不得用现今分类冒充历史真实分类。

Batch 4A 已发现的 12 个异常成员计数日期、29 个股息金额差异、退市结算缺口和历史行业分类缺口，需要按影响程度完成验收。

Norgate 原始数据及历史成员记录必须在许可范围内处理、保留或清理，不得公开上传。

## 9. Study Windows

### Study A — Historical development evidence

现有 2025-09-18 至 2026-10-30 的 282 日研究。

用途：历史现象、机制探索和旧模型分析。

状态：已经反复观察，不能作为独立样本外验证。

### Study B — PIT-corrected historical experiment

在新数据和正式协议下，使用历史成员资格与统一执行模型重新计算历史研究结果。

用途：检查幸存者偏差、历史数据质量和政策比较对数据选择的敏感性。

状态：属于已观察历史上的重新验证，不因更换数据供应商而成为独立样本外实验。

### Study C — Independent confirmation

在研究协议、代码、评价指标和分析规则冻结后，使用未来尚未观察的数据，或者具有可信未检视记录的独立历史区间进行验证。

用途：检验结果能否推广到研究开发期之外。

确认窗口长度必须依据实际研究目标和统计精度决定，不能任意规定 60 日或 120 日便声称具有足够统计功效。

## 10. Mechanism Experiments

计划研究四种机制，每种机制必须有可观测的解释变量和明确的对照。

**M1 — Execution timing**

比较 T 收盘计划后的风险、T+1 开盘成交后的风险，以及 T+1 收盘风险，量化价格与成交时点影响。

**M2 — Stop-gap giveback**

识别持仓浮盈增加、初始止损不变、风险贡献上升与减仓触发之间的关系。

**M3 — Portfolio path divergence**

比较三种政策在相同初始状态和候选信号下如何逐步形成不同持仓，并识别由政策干预引起的后续订单差异。

**M4 — Implementation frictions**

检查佣金、滑点、交易频率和可能的现金闲置如何改变模拟结果。

机制实验应区分直接程序规则、历史观测关系和无法识别的经济因果机制。

## 11. Statistical Analysis

预先定义主要对照、估计量、统计单位和比较方法。

同一天的 A/B/C 结果属于配对的模拟政策路径，但不同交易日并非相互独立的实验复制。

潜在方法包括日期区块重抽样、对序列相关稳健的区间估计，以及超标持续时间分析。

必须在运行正式确认实验前选择具体方法及其参数，并记录多重比较处理方式。

已观察历史上的任何统计区间均只能作为探索性证据。

不预设统计显著性，不以正收益作为实验成功条件。

## 12. Research Integrity and Publication Gates

正式进入 PIT 新回测之前，需要：

1. 历史股票池和信号预热规则验收完成。
2. 价格调整及股息口径已固定。
3. 重大公司行动和退市处理具有可信规则。
4. 历史行业分类得到解决，或明确修改研究对象并经学术审核。
5. 同一执行器下的 A/B/C 规则和持仓状态订单处理已验证。
6. 主指标、比较政策和机制对照在查看新实验结果前冻结。
7. 数据授权、代码环境、配置和审计日志具备可复现路径。

如果任何关键门槛未通过，不得将历史模拟结果表述为已获得投稿级验证。

## 13. Publication Strategy

目标是产生一篇研究 **stop-gap 风险预算的实施效果及经济机制** 的实证论文。

论文的主要贡献应来自机制解释、清晰的实验对照和可信的验证，而不只来自某一策略在某段时间的收益排名。

投稿前还需要独立研究审阅、文献差距验证、长期数据复现安排和目标期刊适配。

**本协议必须经研究者审阅及正式记录后才能成为冻结版本。** 任何未来修改都需要有日期、理由和版本记录，不得追溯改变已经观察过的数据分析规则。