# Batch 4A.10 — controlled event-impact gate

**Decision, 2026-11-02: CONDITIONAL GO for targeted verification and further controlled diagnostics; NO-GO for the official Batch 4B A/B/C/F experiment.** Local Norgate use was explicitly confirmed by the researcher. One exploratory Policy A diagnostic ran with the isolated versioned runner and empty verified-event register. It wrote only an ignored private event classification file; no official policy comparison or performance report was generated.

## Controlled diagnostic evidence

The Policy A path began on the fixed 2025-12-02 calendar and halted on **2025-12-22** at its first actually exposed, unverified event. Before that halt, **114 distinct candidate asset/date events had no actual held or pending-order exposure**. The affected asset was held at the event boundary; there was no pending order for it. Provider evidence indicates a cash dividend, but raw-share terms, entitlement and payment date have not been independently verified. It is therefore classified **MATERIAL_UNRESOLVED_EVENT_BLOCKS_PATH**, not treated as a verified distribution or silently ignored. The private file retains the asset identity, evidence and held quantity. Counts in the requested mutually exclusive classes are: no actual exposure **114**; exposed with verified accounting terms **0**; exposed requiring verification without an immediate accounting block **0**; material unresolved event blocking the path **1**. The blocking event also requires verification, but is assigned the stricter blocked class. Later events cannot be evaluated on this blocked path, and Policy A nonexposure never clears B, C or F.

The minimal repair is to independently verify the affected dividend's ex-date, cash amount per raw share, entitled shares and payment date, enter the source-backed terms in the ignored register, then rerun the same controlled diagnostic. If verification fails, seek approval for a dated common pre-event cutoff or an explicitly hypothetical sensitivity with a narrower claim. Neither alternative is presently authorized. Continue this targeted process only for events that actually affect held shares or pending orders on a proposed path. Do not use provider factors alone as verification.

## Gate matrix

| Gate | Result | Evidence or remaining action |
|---|---|---|
| Local licensed-use permission | **PASS** | Researcher explicitly confirmed local use. |
| Fixed calendar and isolated runner | **PASS** | Existing 230-session gate; controlled Policy A diagnostic used only `--mode diagnostic`. |
| Synthetic integration and accounting | **PASS** | See Batch 4A.9; Batch 4A.10 targeted diagnostic tests and full suite below. |
| Candidate no-exposure classification | **PASS** | 114 private candidate asset/date events through the first blocker; no held or pending shares. |
| First actually exposed Policy A action | **BLOCKED** | 2025-12-22 cash-dividend evidence on a held position lacks independent raw-share terms and payment date. Fail-closed exit 2. |
| Later Policy A actions | **PARTIAL** | Not evaluable after the first blocked event; do not infer no exposure. |
| B/C/F action exposure | **BLOCKED** | Not diagnosed; one-policy result does not establish their holdings. |
| Verified-event register | **PARTIAL** | Private ignored v1 register exists and is empty; no real source-backed terms entered. |
| Hash-bound approval record | **PASS** as draft artifact | Private ignored v1 record binds protocol, SQLite, event register, code, source versions, configuration and diagnostic hash; status is `DRAFT_NOT_APPROVED`. Official guard must reject it. |
| v0.3 protocol decision | **PENDING researcher approval** | Recommendation is in the companion document; protocol remains DRAFT. |
| Official Batch 4B | **NO-GO / BLOCKED** | Material Policy A event, unknown B/C/F event paths and absent dated researcher approval. |

## Private artifacts and approval scope

`restricted_norgate/ng_sf_270_lw_verified_events_v1.json` is the private verified-event register (`[]`, no verified event claims). `restricted_norgate/ng_sf_270_lw_approval_v1.json` is the **unapproved** hash-bound record. `restricted_norgate/ng_sf_270_lw_v1/run_e3cedebe0bedf7ef78b4c838/diagnostic_private.json` stores the exploratory classifications. These files are Git-ignored and contain no publication result. The approval record names the affected asset privately, records the fail-closed treatment, and lists exact researcher requirements. Changing the register, protocol or code invalidates its current hashes.

The files requiring researcher review and explicit approval before an official run are: [the v0.3 protocol](NG_SF_270_LW_PROTOCOL_V03_APPROVAL_DRAFT.md), the private verified-event register, and the private hash-bound approval record. The researcher must review the documented event evidence/treatment and date the final approval; this report grants no approval. A future official run also requires the unchanged code and SQLite hashes to match that approved record.

## Files and bounded verification

Created this report, [the approval recommendation](BATCH4A10_PROTOCOL_APPROVAL_RECOMMENDATION.md), the ignored private verified-event register, approval record and diagnostic output. Modified only the isolated `src/portfolio/ng_sf_270_lw_runner_v1.py`, `scripts/run_ng_sf_270_lw_v1.py` and `tests/test_batch4a9_runner_synthetic.py` to classify candidates and halt at affected unverified terms. Frozen FMA code, previous V4/V5-U outputs and manuscript evidence were not changed. No official A/B/C/F run, acquisition, commit or push occurred.

`python3 -m pytest -q tests`: **PASS, 51 passed, 1 skipped** (the existing skip). The added synthetic diagnostic checks cover both an unexposed candidate followed by an unresolved holding and verified exposed dividend terms. Python compilation of the modified runner, CLI and test: **PASS**. `git diff --check`: **PASS**. `git check-ignore` on all three private artifacts: **PASS**. Calling the official approval guard with the draft record: **PASS**, rejected with `PROTOCOL_APPROVAL_MISSING_OR_MISMATCHED`. The exploratory real-data diagnostic itself exited 2 with `UNRESOLVED_REAL_ACTION`: **BLOCKED as designed**, with no performance output. No bounded synthetic test failed.

The minimum next work is one independent dividend-term verification and bounded rerun, then analogous affected-path checks for B/C/F, followed by researcher approval of the protocol and fresh private hashes. If those gates pass, execute the official versioned policies once, reconcile accounting and logs, and write Manuscript V3 results with the historical-scope limitations and adverse or null outcomes intact.
