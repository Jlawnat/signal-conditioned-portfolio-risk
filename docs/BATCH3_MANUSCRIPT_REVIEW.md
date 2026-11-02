# Manuscript Draft V2 academic review

Review date 2026-11-02. Verdict: **ready for independent human academic review as an exploratory manuscript; not submission ready for strong policy-performance claims.** The Markdown V2 draft is the full source. The LaTeX source is condensed and uncompiled.

| Category | Verdict | Evidence and remaining issue |
|---|---|---|
| Main question and contribution | PASS | A/B/C comparison asks how planned stop-gap budgets change exposure, deployment, costs and realized paths in one fixed implementation. No novel optimality or investable advantage is asserted. |
| Method and notation | CONDITIONAL | Momentum, relative strength, score, exposure, C budget, invested fraction, drawdown and modeled fill cost match inspected code. Full later-state order parity is open. |
| Numerical results and displays | PASS | Source-value validator checks all A/B/C NAV/return/drawdown/invested/cost values, 282 dates, sampled timing, links, SVG and reference differential. V4 and V5-U remain separate. V2 tables are generated from stored outputs. |
| Risk interpretation | PASS | Own-budget days and common 4% days are separated. Planned stop-gap exposure is distinct from realized drawdown and from the hypothetical post-plan state. Residual breaches are reported. |
| Capital deployment | PASS | Invested fraction is called deployment level; efficiency is not claimed or identified. Candidate count is not labeled an executable opportunity count. |
| Dividend and corporate actions | CONDITIONAL | Two curated events and provider-only provisional amounts are separated; narrow endpoint sensitivity is labeled arithmetic. Full action validation and payment calendar remain unavailable. |
| Literature and citations | PASS for eight recorded sources | V2 BibTeX uses the verified 2017 Bailey journal record. Preprints remain labeled. No direct literature claim is made for this exact signal/cash mechanism; one explicit `[CITATION NEEDED]` remains. |
| Statistical design | CONDITIONAL | The hierarchy remains post-hoc. Paired dates, serial dependence, overlap, selected entries and absent untouched holdout are disclosed. No p-values or significance claims. A future confirmation protocol is documented. |
| Reproducibility | CONDITIONAL | Scripts and hashes identify the figure/table pipeline and external local inputs. Raw panels and full extraction provenance are not distributable here; no environment lock. |
| Presentation and LaTeX | NEEDS_REVISION for production | Markdown V2 is complete. Generic LaTeX text/table source exists but is condensed; no LaTeX toolchain was installed, so compilation and final figure placement were not tested. |

## Skeptical claim-to-evidence review

| Claim in abstract/introduction | Supporting evidence | Assessment |
|---|---|---|
| B/C have fewer own-budget exceedance days | `audit/p3_abc_v5u_282_constraints.json`, independently reconstructed V1 risk paths | Supported for observed EOD proxy; no guarantee of compliance. |
| B/C have lower NAV and larger drawdown than A in V5-U | Source-hash-verified comparison and daily outputs | Numerically supported, conditional on simulated fills and dividends. |
| Planned reduction may miss target after next-open fill | Four-stage selected-case replay, especially B/C 2025-10-23 | Supported as a demonstrated example; not a full breach-cause distribution. |
| Candidate scores/ranks match frozen reference | Three full 503-stock dates and prior external differential | Supported on sampled dates; full later-state order parity unresolved. |
| Greater deployment is more efficient | No opportunity-adjusted causal metric | Not claimed. |
| Overlays causally worsen future returns | No randomized/future validation | Not claimed. |

## Final editing check

The abstract gives the design, verified negative returns and scope before interpretation. Method definitions precede results; discussion keeps competing mechanisms separate. A final prose pass removed inflated contribution language and retained technical qualifiers, figures, values and citations. Remaining production tasks are a coauthor/researcher approval of the post-hoc outcome hierarchy, a line edit for target venue style, compilation of a full LaTeX rendering and source permissions review. These do not change the current V2 numerical record.
