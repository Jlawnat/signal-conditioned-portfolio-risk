# Figure sources and captions

Run `python3 scripts/verify_paper_evidence.py`, then `python3 scripts/paper/generate.py`, then `python3 scripts/paper/png_previews.py` from the repository root. Each numbered figure has an SVG master and matching PNG preview. The PNG step uses installed `librsvg` and `libgdk_pixbuf` through Python `ctypes`; no paid API is required. All charts use V5-U simulated data from `audit/p3_lifecycle_v5u_{A,B,C}_daily.csv` and trade files. Risk figures reconstruct holdings with the local historical signal CSV, market bundle and provider manifest, then assert the stored `audit/p3_abc_v5u_282_constraints.json` counts and means.

| Number | File stem | Caption |
|---|---|---|
| 1 | `fig01_nav` | Daily simulated NAV for A/B/C, 282 sessions, V5-U; axis begins at $900,000 and is labeled. |
| 2 | `fig02_drawdown` | Daily percentage drawdown from the running NAV peak, including initial $1 million. |
| 3 | `fig03_planned_risk` | Daily end-of-day stop-gap exposure (solid) and each policy's own T-close budget (dashed); this is not realized loss. |
| 4 | `fig04_fixed_reference` | The same stop-gap exposure against a common fixed 4% reference; C may legitimately have an own budget above 4%. |
| 5 | `fig05_deployment` | Daily invested market value divided by NAV. |
| 6 | `fig06_breaches` | Counts of observed end-of-day days above own budget, common 4% and 24% sector reference. |
| 7 | `fig07_trades` | Buy plus sell fill counts under V5-U. |
| 8 | `fig08_costs` | Modeled commission plus adverse slippage costs under V5-U. |
| 9 | `fig09_policy_budgets` | Daily policy budget schedule. |
| 10 | `fig10_cash` | Daily cash divided by NAV; dividend receivables are separate. |

Colors are consistent: A blue, B orange, C purple. Axes are shown in actual units and all daily observations are plotted without smoothing. The generated SVG/PNG files and tables are derived products; historical `audit/` files remain untouched.
