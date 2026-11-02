# Batch 3 validation record

Executed from `/home/elliot/signal-conditioned-portfolio-risk` on 2026-11-02. No full 282-session strategy experiment was rerun. The scripts below read existing outputs; the two differential scripts wrote only new V2 JSON artifacts, and the V2 generator wrote new tables/figure.

| Exact command | Final result |
|---|---|
| `python3 scripts/verify_paper_evidence.py` | PASS: A/B/C four stored output hashes each, 282 sessions each, 313/464/478 fills, NAV/return/drawdown; two frozen FMA hashes. |
| `/home/elliot/FMA_Independent_Research/.venv/bin/python -m unittest discover -s tests -v` | PASS: 19 tests; persistent 408/408 managed-position exit cases. |
| `/home/elliot/FMA_Independent_Research/.venv/bin/python scripts/paper/batch3_fidelity.py` | PASS on preselected three 503-stock dates: 9/40/21 candidates with exact rank, score, setup, adjusted stop; eight first flat-account target quantities matched V5-U A fills. Full order history remains untested. |
| `python3 scripts/paper/batch3_risk_timing.py` | PASS: wrote nine selected breach transitions to `paper/tables/v2/risk_timing_sample.json`; selected T-close, hypothetical after-sell, T+1 post-fill open and close states reported. Not a full 282-day cause decomposition. |
| `python3 scripts/paper/generate_v2.py` | PASS: three Markdown tables and one SVG generated from source JSON/fills; curated entitlement check asserted $404.63/$490.70/$489.19. |
| `python3 -m py_compile scripts/paper/batch3_fidelity.py scripts/paper/batch3_risk_timing.py scripts/paper/generate_v2.py scripts/paper/validate_v2.py` | PASS. |
| `python3 scripts/paper/validate_v2.py` | PASS: main numbers against stored results, breach counts, sampled differential and timing, bibliography entries, local links, SVG and date/policy labels. |
| `python3 scripts/paper/validate.py` | PASS: V1 eight-section assembly, ten SVG/PNG pairs, five tables and source numbers remain valid. |
| `git diff --check` | PASS for tracked diff. |
| `python3 -c '…new-artifact whitespace/newline check…'` | PASS: 25 new V2 text/code/artifact files, zero trailing-whitespace or final-newline failures. |

Two preliminary QA commands failed because of **checker syntax**, then passed after correction: the first V2 validator expected ASCII minus signs while the manuscript uses Unicode minus; it now normalizes only for numeric matching. The first ad hoc whitespace command tested against a literal backslash-n instead of a newline byte; the corrected command used `bytes([10])`. Neither failure indicated a source-value discrepancy. No failed research regression remains.

**NOT_TESTED / conditional:** full frozen FMA order parity after positions exist; all 282-session breach-cause attribution; official payment evidence for provider-only dividends; point-in-time index membership; independent raw-panel redistribution and extraction provenance; an untouched future holdout; LaTeX compilation (no `pdflatex`/`latexmk` in this environment). No p-values or statistical significance test were added.
