# Batch 4A price adjustment specification — proposed, not approved

Norgate's [data FAQ](https://norgatedata.com/data-package-faq.php) defines `NONE` as unadjusted OHLCV, `CAPITAL` as adjusted for capital reconstructions, `CAPITALSPECIAL` as capital plus special distributions, and `TOTALRETURN` as capital plus special and ordinary distributions. Historical volume is adjusted reciprocally for capital reconstructions; turnover is never adjusted. The [Python documentation](https://pypi.org/project/norgatedata/) states that `price_timeseries` defaults to total return, so Batch 4A explicitly requests **all four** modes and `padding_setting=PaddingType.NONE`. The `Dividend` column reflects only distributions *not already adjusted into that mode*: CAPITAL includes ordinary and special; CAPITALSPECIAL includes ordinary; TOTALRETURN includes none. Entitlement appears on the close before ex-date.

| Research use | Proposed Norgate input | Rule and unresolved check |
|---|---|---|
| Hypothetical T+1 open execution and daily position marks | `NONE` Open/Close and OHLC | Use actual quoted unadjusted units; no filled price invented where no bar exists. |
| Technical momentum, EMA, stops and comparison with old adjusted panel | `TOTALRETURN` OHLCV | Candidate mapping, subject to parity check against frozen feature inputs. This view is signal-only; portfolio P&L must not mark in total-return units while also crediting dividend cash. |
| Split-aware indicator sensitivity | `CAPITAL` OHLCV | Preserved separately to isolate reconstruction factors and compare signal behavior. |
| Special-distribution sensitivity | `CAPITALSPECIAL` OHLCV | Preserved separately; special cash/stock economics require independent terms. |
| Dividend cash accrual | `NONE` or `CAPITAL` `Dividend`, cross-checked with CAPITALSPECIAL | Use entitlement at prior close only for shares then held. Determine ordinary versus special using differences between modes; confirm event terms and payment dates independently. Never add TOTALRETURN price return to cash accrual. |
| Split position quantities | Capital-event flag plus independently documented ratio and effective date | Flag is a detection aid, not a ratio. No split-adjusted quantity is inferred from price factors alone. |
| Liquidity and turnover | `NONE` Volume and Norgate Turnover | `NONE` volume is traded share units. Adjusted volume belongs only with its adjusted-price signal view; turnover is unadjusted across modes. Verify whether frozen liquidity uses raw or adjusted volume before parity claim. |

At each date, `adjusted_close / raw_close` is a conversion factor for that acquisition's adjusted view. It can be used to express a signal stop in raw *same-date* units; it is not a sufficient corporate-action ledger. Factor jumps, cash distributions and reconstructed shares must be independently checked around events. No payment dates, merger consideration, or split ratios are invented. Future provider revisions can change factors.

**Approval gate:** The researcher must approve the exact indicator view, raw execution/mark view, dividend entitlement and payment policy, split-quantity event source, and treatment of special distributions before any PIT portfolio simulation. The previous V5-U run is not retrospectively recast as Norgate-based.
