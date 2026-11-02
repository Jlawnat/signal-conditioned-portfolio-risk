# Batch 4A member coverage report

The full local extraction covered **544 Current/Past candidates plus SPY** and produced 244,943 dated price rows in each of the four explicit adjustment views, 979,772 price rows total. It had **zero extraction errors**. Norgate SPY dates matched the existing **282-session** study calendar exactly, from 2025-09-18 through 2026-10-30. The range began at 2025-01-02 to supply pre-window history.

| Measure over 282 study dates | Aggregate result |
|---|---:|
| Daily S&P 500 membership count | 502–504; 503 on 270 dates, 502 on 6, 504 on 6 |
| Member count at first/last study date | 503 / 503 |
| Explicit observed 0→1 / 1→0 transitions | 27 / 20 |
| Member date observations lacking 126 earlier bars | 373, across 5 securities |
| First to last study date of those insufficient histories | 2025-10-30 to 2026-10-30 |
| Price bars on study dates without membership 1 | 7,856 |
| Candidate series with last price before study end | 14 |
| Delisted-database candidates with prices in extraction range | 14 of 16 |
| Extraction errors / invalid OHLCV / duplicate records | 0 / 0 / 0 |
| Internal price-calendar gaps within candidate trading spans | 0 |

The five short-history securities first traded after the requested 2025-01-02 start. Their insufficiency is real within the available history, rather than a simple failure to request enough pre-window data. They must be ineligible for a 126-session momentum signal until 126 **actual prior bars** exist. The 27 additions and 20 removals are transitions with observed flags on successive study dates; terminal disappearance after a last quoted bar is not counted as an explicit removal. This is why those transition counts do not arithmetically explain the first/end counts.

The 12 dates with 502 or 504 members are anomalies for review, not forcibly set to 503. Norgate permits non-500 counts because an index may contain multiple share classes and effective-date changes can overlap. The extractor's no-padding membership rows align to security trading observations, so the observed zero “member without price” count is **not independent proof** that halts or terminal days had no missing member prices. The 14 last-price-before-end cases, including 13 delisted candidates with a membership 1 on the last quoted bar, need terminal-event evidence. Two of the 16 delisted candidates had no price within the requested 2025 onward range; the earlier researcher check of all 16 used a wider historical query.

The earlier two-date access checks found 503 members with prices at both endpoints and zero errors, consistent with this full extraction. The `QRVO-202610` example had 479 price bars and only 34 membership days over that earlier wider range; price availability is not membership.

The private SQLite contains daily source rows. This public report contains only aggregate quality statistics. A per-date or per-security membership table is licensed Content and will not be versioned here.
