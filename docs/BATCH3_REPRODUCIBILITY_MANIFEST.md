# Batch 3 reproducibility manifest

Recorded 2026-11-02. Base repository HEAD: `0ff4ee1fa3c24b91d34e261f19bbd7025764d60e`; the working tree contains pre-existing uncommitted Batch 1/2 material and the separate V2 additions. No commit was made. `python3 --version` reported 3.14.4; the existing local research venv reported pandas 3.1.0 and NumPy 2.5.4. Standard-library generation scripts run with system Python; the frozen-reference differential and test suite use `/home/elliot/FMA_Independent_Research/.venv/bin/python`. No dependency lock or distributable market-data package exists.

## Source identity and external local inputs

| Input | Location / SHA-256 | Origin and limitation |
|---|---|---|
| Frozen MPB implementation | `~/FMA_Competition/fma_mpb_v41_20261013/fma_mpb_v41/momentum_pullback_breakout.py`; `5087335538c2670e9f6e405fab9a19a0186ee6efcae95ca4dc57c6502a268a21` | Original FMA reference, read only. |
| Frozen config | Same directory, `config.py`; `152f0d483216d255d6be5dc3281475f3df81ec1224c4e7ee45a9f1d51995e283` | Read only. |
| Candidate CSV | `~/FMA_Independent_Research/audit/historical_signal_candidates.csv`; `3b3b42573ec0333e0960538ad158675a2e3bf49308f3922e361c00322770323f` | Prior local signal-generation artifact; full lineage and PIT membership uncertified. |
| Universe lineage | `~/FMA_Independent_Research/audit/universe_lineage.csv`; `d062ae9cb7d77fc554033d61b2f09443fc5f4edd0e09a8550425a820717d3827` | 503 retrospectively current stocks, not historical PIT membership. |
| Market bundle | `~/FMA_Competition/Market_Refresh_Runs/manual_full_20261031T061137Z_432cf6e9/market_bundle/{raw,adjusted,manifest.json}`; manifest `547e69e3c5455ab7dddff3a3b66ad05d48d2f877c324b2f241b2fdf566e83c6a` | Local provider OHLCV and action data; rights and original extraction metadata are outside this repository. Individual panels were not hashed here. |
| Dividend register | `configs/verified_cash_dividends.json`; `09f201cbffa127fe9df9b4d77c4f607ab1aaa7f80b2b33d874c424e041979b23` | Two curated events. The file was already modified before Batch 3; its current hash records the state used for this audit. |

## Authoritative outputs and generated artifacts

`audit/p3_abc_v5u_282d_comparison.json` (SHA-256 `2627dd853831963397e0cc7bbdf6f54f0ee85f658e325427cf911835eaf57a53`) and `audit/p3_abc_v5u_282_constraints.json` (`78d6ff048c0627b4362cd2436f0faab9ed84c572d42207275582a93a45de10bf`) are the V5-U aggregate sources. The comparison file holds twelve A/B/C output hashes. Daily and fill inputs are `audit/p3_lifecycle_v5u_{A,B,C}_{daily,trades}.csv`; source hashes are verified by `scripts/verify_paper_evidence.py`. V4 values come only from `audit/p3_abc_282d_comparison.json` and remain separate.

The V1 figure source is `scripts/paper/generate.py`, whose risk reconstruction checks V5-U aggregate counts; the original V1 figures and tables are reused unchanged in V2. `scripts/paper/batch3_fidelity.py` generates `paper/tables/v2/fidelity_differential.json`. `scripts/paper/batch3_risk_timing.py` generates `paper/tables/v2/risk_timing_sample.json`. `scripts/paper/generate_v2.py` generates three V2 Markdown tables and `paper/figures/v2/fig01_timing.svg`. Figure/table source mapping is in their `README.md` files. `paper/MANUSCRIPT_DRAFT_V2.md` is the full manuscript; `paper/latex_v2/main.tex` is a condensed portable rendering and was not compiled because no LaTeX toolchain was found. `paper/references_v2.bib` is the reviewed bibliography.

## Reproduce without rerunning a strategy search

From the repository root, with the documented local inputs present:

```sh
python3 scripts/verify_paper_evidence.py
/home/elliot/FMA_Independent_Research/.venv/bin/python -m unittest discover -s tests -v
/home/elliot/FMA_Independent_Research/.venv/bin/python scripts/paper/batch3_fidelity.py
python3 scripts/paper/batch3_risk_timing.py
python3 scripts/paper/generate_v2.py
python3 scripts/paper/validate_v2.py
python3 scripts/paper/validate.py
git diff --check
```

The last two validators read the manuscript and displays; they do not rerun 282-session policy experiments. An authorized independent researcher would need a licensed copy of the same raw/adjusted daily panels and action manifest, the frozen source at the recorded hashes, the candidate and current-universe lineage artifacts, the same dividend register and an environment matching the recorded dependencies. The present manifest does **not** promise exact third-party reconstruction from public repository files. No raw proprietary panels, account credentials or StockTrak identifiers were copied into Batch 3 artifacts. A portable data extraction specification and dependency lock remain future work.
