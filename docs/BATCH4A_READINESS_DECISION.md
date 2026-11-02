# Batch 4A data-readiness decision

Batch 4A integration and audit work is **complete** as a bounded data-quality pass. The newly extracted Norgate input is **not approved for a PIT portfolio replay**. The original 282-session V5-U results, frozen FMA implementation, configs and manuscript drafts are unchanged.

| Gate | Status | Evidence / condition |
|---|---|---|
| DATA_ACCESS_READY | PASS | Windows Python 3.14 and Norgate 1.0.77 worked from WSL; 544 candidates and SPY extracted with zero API errors. |
| PIT_UNIVERSE_READY | PARTIAL | 282 dates match; daily members 502–504. Twelve non-503 dates require effective-date review; five new listings have 373 member dates without 126 prior bars; no-padding membership cannot independently expose member price gaps on halts/termination. |
| PRICE_ADJUSTMENT_READY | PARTIAL | All four explicit modes and no-padding data captured; proposed runner mapping and dividend non-duplication rule documented. Researcher approval and event-level parity checks remain. |
| CORPORATE_ACTION_READY | FAIL | 29 legacy dividend amount discrepancies; 12 capital flags need event terms; 13 delisted series end while last quoted membership is 1; terminal consideration and full payment calendars are missing. |
| HISTORICAL_SECTOR_READY | BLOCKED | Norgate supplies current classification only. Monash/WRDS historical GICS is a possible licensed route, not yet verified accessible or joined. |
| READY_FOR_VERSIONED_PIT_EXPERIMENT | BLOCKED | Depends on all unresolved gates and a separately frozen protocol/approval; no A/B/C simulation was run. |

## Exact next milestone

1. Resolve the 12 unusual membership dates against effective-date index notices or a suitable independent source; check halts and terminal-date missing-price exposure with a method that does not infer membership from an OHLCV bar. Confirm stable asset-ID joins and external historical ticker/class mappings.
2. Predeclare that a member needs 126 actual prior valid stock and SPY bars for the frozen momentum signal. Approve treatment of the five new listings and any other missing features; do not forward-fill prices.
3. Approve the price-view map in `BATCH4A_PRICE_ADJUSTMENT_SPEC.md`. Reconcile the 29 private dividend exceptions, independently document split/merger/distribution terms and payment dates needed by accounting, and resolve the 13 last-member terminal series before hypothetical holdings could cross them.
4. Confirm licensed access to effective-dated historical sectors and security-level joins for all candidate dates, or explicitly redesign the 24% constraint under a separately named research question. Do not label current sectors PIT.
5. Only then write and approve a new, independent PIT historical experiment protocol with frozen input checksums, event accounting, estimands, signal/order fidelity scope and output paths. Keep V5-U as the untouched historical reference.
