# NG-SF-270-LW co-dated cash dividend rule — approval draft

Status: **DRAFT; researcher approval required before official Batch 4B**. This is an accounting representation for the isolated NG-SF-270-LW experiment. It does not alter the frozen FMA strategy.

## Observed exposed event

CME Group declared two distinct USD cash dividends on 2026-02-12: a regular $1.30 and annual variable $6.15 per common share. Both have 2026-03-10 ex and record dates and 2026-03-26 payment dates. The [issuer dividend history](https://cmegroupinc.gcs-web.com/dividend-splits-iframe) lists both rows, and the [issuer announcement](https://investor.cmegroup.com/news-releases/news-release-details/cme-group-declares-annual-variable-dividend-and-q1-2026) describes both components. The exploratory Policy A path held 81 raw shares at the preceding close. The local provider's $7.45 observation is only a cross-check.

## Proposed narrow rule

When two or more independently verified **cash-only** dividends for the same asset have identical declaration, ex, record, payment, currency, raw-share basis and entitled-share population, represent them as one aggregate `CashDividend` in the private register. Preserve each source component in the private evidence record. The aggregate cash per raw share is their exact decimal sum. Apply one receivable and one stop adjustment equal to that sum on the ex-date; release the receivable on the common payment date. Reject aggregation if any field differs, a split or other action is co-dated, or terms are missing. Do not use provider totals as evidence.

For CME this produces $7.45 per raw share, $603.45 receivable on 81 shares, and a $7.45 held-stop adjustment. Addition is commutative for these two cash terms; the result equals separate accruals and separate stop reductions before any intervening execution. The accounting API still blocks multiple registered actions for one asset and day. This rule permits only the prevalidated single cash representation and requires a synthetic equivalence test.

The same proposed rule also applies to the exposed Host Hotels & Resorts 2026-06-30 distribution. Its [issuer 10-Q](https://www.hosthotels.com/-/media/HostHotels/Files/DownloadLinksAssets/10-Q/2026/Host_Hotels_Resorts_Inc_2026_Q1_10-Q.pdf) describes one $0.92 common-share cash dividend composed of $0.20 regular plus $0.72 special, both declared on 2026-05-06, record 2026-06-30 and payable 2026-07-15. The private register represents the issuer's stated combined $0.92, with both components retained in evidence. The proposed additive rule must cover this case expressly at approval.

The researcher must approve this rule with the V0.3 protocol before the official run. Until then, diagnostic continuation using this representation is exploratory and the official approval gate remains closed.
