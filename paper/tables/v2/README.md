# V2 table provenance

Run `python3 scripts/paper/batch3_risk_timing.py`, then `python3 scripts/paper/generate_v2.py` from the repository root. `table01_risk_timing.md` uses immutable V5-U daily and trade files plus raw/adjusted price panels. `table02_deployment.md` uses `audit/p3_abc_v5u_282d_comparison.json` and the stored candidate CSV. `table03_dividends.md` uses the same comparison JSON and independently counted USB/CAT ex-date entitlements; the latter arithmetic is documented in `docs/BATCH3_CORPORATE_ACTION_AND_RISK_TIMING.md`. The generated `fidelity_differential.json` comes from `scripts/paper/batch3_fidelity.py` using the frozen FMA source, current-universe lineage, price panels and candidate CSV.

V2 reuses V1 Tables 1–5 without numerical edits. Their provenance and generation command are in `paper/tables/README.md`. All new analyses are post-hoc exploratory. The endpoint receivable subtraction is a component calculation, not a new simulated NAV path.
