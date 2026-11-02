# Batch 2 validation record

Executed from the repository root on 2026-11-02. All listed final commands exited 0.

| Command | Observed result |
|---|---|
| `python3 scripts/verify_paper_evidence.py` | A/B/C: four hashes each, 282 sessions each, 313/464/478 fills, NAV/return/drawdown PASS; two frozen FMA source hashes PASS. |
| `/home/elliot/FMA_Independent_Research/.venv/bin/python -m unittest discover -s tests -v` | 19 tests passed, including the one persistent test with 408/408 managed-position exit subcases. |
| `python3 scripts/paper/generate.py` | Ten SVG figures and five Markdown tables generated; reconstructed V5-U own-budget, fixed-4%, sector counts and mean risk matched independent audit. |
| `python3 scripts/paper/png_previews.py` | Ten PNG previews rendered from SVG masters. |
| `python3 scripts/paper/assemble.py` | Eight sections assembled into unified Draft V1. |
| `python3 scripts/paper/validate.py` | Eight sections, ten SVG/PNG pairs, five tables, eight bibliography entries, authoritative main values, local links and image structure PASS. |
| `git diff --check` | No whitespace errors in tracked-file diff. New files were also checked for trailing whitespace and final newlines separately. |

An initial run of the new parity test failed because the test harness grouped context managers as a tuple. That syntax was corrected before any comparison ran; the subsequent 408-case run and full suite passed. No frozen source, historical simulation output or prior audit was changed. No 282-session experiment was rerun.

Remaining unexecuted checks: full historical reference signal/order parity, all-event independent dividend/payment verification, four-state V5-U breach timing, a point-in-time universe and an untouched holdout. The absence of Matplotlib and LaTeX tools did not block vector SVG/PNG generation or the Markdown manuscript. The figures use installed local `librsvg` and `libgdk_pixbuf`; no paid API was used.
