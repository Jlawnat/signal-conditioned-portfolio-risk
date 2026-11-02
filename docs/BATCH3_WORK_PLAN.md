# Batch 3 research validation and Manuscript V2 plan

Status: completed for Manuscript Draft V2 on 2026-11-02. This plan tracks the user-authorized Batch 3 work; it creates no approval gate. Remaining scientific limitations are recorded in the validation reports and manuscript review.

| Stage | Files | Completion criterion |
|---|---|---|
| Bounded signal/order comparison | `scripts/paper/batch3_fidelity.py`, `docs/BATCH3_SIGNAL_ORDER_FIDELITY.md` | Source hashes; candidate/feature/rank checks on predeclared dates; focused planner comparison; explicit PASS/PARTIAL/FAIL/NOT_TESTED. |
| Dividend and timing attribution | `scripts/paper/batch3_risk_timing.py`, `docs/BATCH3_CORPORATE_ACTION_AND_RISK_TIMING.md` | Reconcile event/receivable counts; narrow endpoint sensitivity; reconstruct selected preplan/postplan/post-open/close states without rerunning history. |
| Outcome and statistical framing | `docs/BATCH3_CAPITAL_DEPLOYMENT_FRAMEWORK.md`, `docs/BATCH3_STATISTICAL_VALIDITY_PLAN.md` | Separate deployment level from efficiency; state dependence, feasible exploratory analysis and future confirmation protocol. |
| References and displays | `paper/references_v2.bib`, `docs/BATCH3_LITERATURE_VERIFICATION.md`, `paper/{figures,tables}/v2/` | Verify metadata and final Bailey record; reuse correct V1 assets, add only material V2 figures/tables. |
| Manuscript | `paper/MANUSCRIPT_DRAFT_V2.md`, optional `paper/latex_v2/` | Complete revised argument with equations, author-year citations and evidence-qualified conclusions. |
| Quality control | `docs/BATCH3_MANUSCRIPT_REVIEW.md`, `docs/BATCH3_REPRODUCIBILITY_MANIFEST.md` | Recompute displayed numbers, run focused tests, record exact commands and remaining limitations. |

Global constraints: frozen FMA read-only; no historical result edits; no parameter search or 282-session strategy rerun; preserve V1; no commit/push; use local inputs and free primary academic sources. Review focus: candidate/rank mismatches; planned versus executed risk; dividend cash versus receivable; 4% common versus own budget; references that changed publication status.
