# Batch 4A point-in-time universe audit

## Method

The independent Windows extractor takes the Norgate `S&P 500 Current & Past` watchlist as a **candidate set**, resolves each symbol to a stable Norgate asset ID, then separately queries `index_constituent_timeseries(asset_id, "S&P 500")`. Eligibility on decision date T is the membership indicator at T, subject to a valid T price and 126 prior observed stock bars for the longest frozen momentum calculation. Current/Past presence and an OHLCV bar alone do not establish eligibility. Norgate's [index FAQ](https://norgatedata.com/data-package-faq.php) says additions/removals described as effective before the open appear with the new state on that effective date. This is the provider's historical membership series at the acquisition date; it is not a provider-versioned vintage of what the database displayed on T.

The validator compares Norgate SPY dates to the existing 282-session raw SPY study calendar; it does not synthesize weekdays. It counts 0→1 and 1→0 transitions only when both successive study sessions have observations. A missing indicator row is kept distinct from explicit 0. It checks member price availability, 126 actual prior bars, duplicate asset/mode/date records, valid OHLCV, adjustment-view date alignment and last price dates. Price padding is disabled. The candidate is keyed by asset ID, not historical symbol text, because symbols can change. A separate effective-dated symbol history is still needed for external joins and order display.

## Current result

Full-extract aggregate results are in [the member coverage report](BATCH4A_MEMBER_COVERAGE_REPORT.md). The 544-candidate acquisition has zero source errors and its SPY calendar matches all 282 study dates. Membership is 503 on 270 dates and 502 or 504 on 12 dates. Five newly listed members contribute 373 member dates with insufficient 126-bar history. The first and last dates each have 503 observed members; this agrees with the researcher’s prior two-date access checks but does not resolve every intervening effective-date anomaly.

## Interpretation limits and anomaly triage

Norgate's membership indicator queried with `PaddingType.NONE` aligns to each security's available trading observations. Therefore a zero count of “member but no price” in this first extract could be structural, **not proof of no missing member prices** on halts or immediately after termination. No membership rows were missing *inside* any extracted price span, but the 12 non-503 dates and terminal last-price cases need targeted effective-date review. Norgate's delisted-symbol suffix is the last-traded year/month, not an index-removal date ([NDU FAQ](https://norgatedata.com/ndu-faq.php)). The 7,856 price bars without membership 1 demonstrate that listed former members are not simply treated as eligible. Securities that cease trading need separate terminal economics; no last-close liquidation is assumed.

**Gate:** A PIT-corrected experiment requires a fully reconciled 282-date membership/price panel, no unexplained active-member gaps or identifier collisions, sufficient lookbacks, and independently supported terminal treatment. The universe extract itself does not authorize replay.
