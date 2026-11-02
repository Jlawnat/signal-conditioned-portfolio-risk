# Batch 4A.11 — final controlled diagnostic and approval readiness

**Decision, 2026-11-02: CONDITIONAL GO for researcher approval; NO-GO for an official Batch 4B run until explicit dated approval.** The fixed NG-SF-270-LW window remains 2025-12-02 through 2026-10-30 (230 sessions), with 270 aligned stock/SPY bars. The four controlled paths used the existing isolated runner and private event register. They generated no official comparative performance results. This is previously inspected historical research, not independent out-of-sample confirmation.

## Controlled paths and accounting gates

| Policy | Diagnostic | Sessions / decision-open pairs / S0–S5 snapshots | Exposed cash-dividend keys | Independent arithmetic audit | Orders accepted / filled |
|---|---|---:|---:|---|---:|
| A | **PASS**, `run_b22b451ece65cec9af83a02b` | 230 / 229 / 1,374 | 28 | **PASS** | 283 / 283 |
| B | **PASS**, `run_0fe9807092cc63c1cc8a15d7` | 230 / 229 / 1,374 | 37 | **PASS** | 363 / 363 |
| C | **PASS**, `run_a784d752e2738531a4b4dcc8` | 230 / 229 / 1,374 | 35 | **PASS** | 384 / 384 |
| F | **PASS**, `run_53a9b9109f1ba0f07508eb1d` | 230 / 229 / 1,374 | 34 | **PASS** | 359 / 359 |

Each path scanned 1,520 candidate event keys. The union of actually exposed keys is **44**, exactly matching the 44 unique, source-documented keys in the private register; there are zero exposed-unregistered and zero registered-unexposed keys. The register contains the previously verified JCI, STLD, NEE, HUBB and DD entries without duplication. All exposed events were cash dividends. Actual split and terminal-event counts were zero across these paths; their handling has synthetic coverage only. No affected path was shortened, and no security was silently removed.

The read-only real-path audit independently checked the fixed calendar, first $1 million close, opening and closing NAV identities, cash and receivable roll-forward, entitlement on prior-close raw holdings, payment dates or post-window lower bounds, dividend-stop adjustments including pending buys, fill costs and cash changes, complete order states and position changes, S2-to-S4 risk-gap arithmetic, and decision/execution information cutoffs. It found **PASS** for all four paths, including no duplicate event key or double dividend accrual. Non-interference comparison to earlier controlled journals found identical economic snapshots through the common prefixes: A 1,374; B 1,278; C 1,302; F 1,302. The current diagnostic is an accounting check; it is not an official outcome estimate.

## Explicit source-treatment decisions before approval

There is **no currently exposed unsupported terminal or split event** and no unmatched material corporate-action key. Four documented treatments still require the researcher's explicit protocol decision:

1. **CME and HST co-dated cash components:** approve the narrow additive treatment in [the separate rule draft](NG_SF_270_LW_CME_CODATED_CASH_RULE_APPROVAL_DRAFT.md). Mixed or unequal-term composites continue to fail closed.
2. **SYY, 2026-07-02:** the [issuer notice](https://investors.sysco.com/annual-reports-and-sec-filings/news-releases/2026/04-17-2026-213525150) states record and payment terms, while its [history widget](https://investors.sysco.com/stock-information/dividend-history) lists July 1 as ex-date. The diagnostic used July 2 based on the [NYSE T+1 rule](https://www.nyse.com/trade/ex-date-dividends) and local event flag. Approve this documented precedence or obtain a definitive correction before an official run.
3. **STLD, 2025-12-31:** the [SEC-filed issuer release](https://www.sec.gov/Archives/edgar/data/1022671/000110465925108723/tm2530635d1_ex99-1.htm) says payable *on or about* January 9; [issuer Form 4 dividend-equivalent credits](https://www.sec.gov/Archives/edgar/data/0001022671/000102267126000018/xslF345X05/form4.xml) corroborate that date but do not prove exact common-share settlement. January 9 was modeled. The A/B/C/F entitlements were $71.50/$76.50/$177.00/$68.50, and the minimum spendable cash after opening buys from January 9–16 exceeded $408,000 across paths, so this timing uncertainty did not constrain those fills. Approve the timing treatment with its caveat or resolve exact settlement evidence.
4. **P&G, 2026-10-23:** the [issuer announcement](https://www.pginvestor.com/news/news-details/2026/PG-Declares-Quarterly-Dividend/default.aspx) says payment *on or after* November 16, after the study close, without an exact day. B held entitled shares. The proposed rule keeps an unpaid receivable through October 30 and fails closed if a future simulation reaches November 16 without exact terms. Approve this bounded rule; do not record an invented payment date.

These are **PARTIAL source-precision and rule-approval gates**, not claims of exact issuer confirmation. Any different treatment changes the protocol, register or code hash and requires a fresh audit and approval record.

## Hash-bound approval package

The ignored private artifacts are `restricted_norgate/ng_sf_270_lw_verified_events_v1.json`, `ng_sf_270_lw_event_evidence_v1.json`, `ng_sf_270_lw_event_audit_v2.json`, and `ng_sf_270_lw_approval_v2.json`, plus four versioned diagnostic journals under `restricted_norgate/ng_sf_270_lw_v1/`. All four private files pass `git check-ignore`. The approval record status is **`DRAFT_NOT_APPROVED`**, with no approval date. Calling the official guard rejects it with `PROTOCOL_APPROVAL_MISSING_OR_MISMATCHED` (**PASS**, fail closed). Every recorded file and manifest hash checked against the current files (**PASS**).

| Approval-bound item | SHA-256 |
|---|---|
| Protocol V0.3 draft | `c251ef05681dc9c544821b262c9f3148d32036d232e93a706f718ae0008b03e8` |
| Norgate SQLite input | `8115412588de1b10ff920d6986c184da78920077117755c7e3111fa7f4f874d4` |
| Private event register | `ad91a02ae1d48da9e5ab8becaef0e3074880c3962a6ec397700c6fe78df304a2` |
| Private event evidence | `f58c9f041b4bdac00264a07cb44d6ea8fe0841819fc05a99c86ac15652ace2ca` |
| Runner | `4e77e40a80938e94422110bffa6472433c954737cada273f6a5378cfa6d5dd50` |
| Code manifest | `7224061c407d0e01648262bea213bac6dfdd00ab353fd93e9e510509330d8d90` |
| Combined data manifest | `bb721701291276ba12a598233ec6b0d41e934cc62c41abc5c66a5001a8184127` |
| CME/HST rule draft | `ae1ebd153547b2018398d47909178d8e256f1f8a8dff825c22c73a2dcea0b459` |

The private approval record also binds the input adapter, action engine, logging code, frozen feature source, risk and exit configuration, auditor and diagnostic journal hashes. The precise approval scope is official A/B/C on the fixed 230-session window, with F **only if explicitly approved**. The prespecified primary B–A outcome uses common 4% excess closing risk; S2-to-S4 implementation gaps, C/F secondary comparisons, bootstrap uncertainty, missingness and accounting conventions are fixed in [protocol V0.3](NG_SF_270_LW_PROTOCOL_V03_APPROVAL_DRAFT.md). No metric or parameter was chosen from these diagnostic paths' performance.

## Gate results and next action

| Gate | Result |
|---|---|
| Four full controlled paths and 44-event exposure union | **PASS** |
| Real-path cash, receivables, NAV, costs, risk and S0–S5 reconciliation | **PASS** |
| Real-path splits and terminal settlements | **PARTIAL** — no actual exposure; synthetic tests pass |
| Source precision and co-dated/post-window accounting-rule decisions | **PARTIAL** — explicit researcher approval pending |
| Synthetic suite | **PASS** — 55 passed, 1 existing skip |
| `git diff --check`, private ignore status, hash check, draft approval guard | **PASS** |
| Official Batch 4B authorization and run | **BLOCKED** — no researcher approval; no official outputs generated |

**Minimum remaining work:** review and explicitly approve [protocol V0.3](NG_SF_270_LW_PROTOCOL_V03_APPROVAL_DRAFT.md), [the CME/HST additive rule](NG_SF_270_LW_CME_CODATED_CASH_RULE_APPROVAL_DRAFT.md), the four source/treatment decisions above, the exact private register/evidence/audit, and the private approval record; decide whether F joins the official scope. Then date the approval record through the documented process, recheck its hashes and run only the approved official policies. If a new material event or accounting failure appears, halt. Review Batch 4B outputs before any separately approved Batch 4C analysis or Manuscript V3 empirical update.

This batch created the private source evidence, final event audit, approval V2 and versioned diagnostic journals, plus this public readiness report and the additive-rule draft. It extended the private event register; modified only the isolated NG-SF runner, corporate-action layer, diagnostic cache and read-only auditor, the V0.3 draft, and focused synthetic tests. Earlier Batch 4A documents, pre-existing working-tree changes, frozen FMA code, V4/V5-U outputs and manuscript evidence were not overwritten. No official experiment, commit or push occurred.
