"""Read-only numerical, citation and artifact consistency checks for Draft V2."""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
TEXT = (PAPER / "MANUSCRIPT_DRAFT_V2.md").read_text()
NUMERIC_TEXT = TEXT.replace("−", "-")
MAIN = (PAPER / "tables/table02_main.md").read_text()
RISK = (PAPER / "tables/table03_constraints.md").read_text()
V2_DIV = (PAPER / "tables/v2/table03_dividends.md").read_text()
COMP = json.loads((ROOT / "audit/p3_abc_v5u_282d_comparison.json").read_text())
CON = json.loads((ROOT / "audit/p3_abc_v5u_282_constraints.json").read_text())
TIMING = json.loads((PAPER / "tables/v2/risk_timing_sample.json").read_text())
FIDELITY = json.loads((PAPER / "tables/v2/fidelity_differential.json").read_text())
assert COMP["sessions"] == 282 and COMP["start_date"] == "2025-09-18" and COMP["end_date"] == "2026-10-30"
for item in COMP["results"]:
    for value in (f'{item["ending_nav_usd"]:,.2f}', f'{item["total_return_pct"]:.4f}',
                  f'{item["max_drawdown_pct"]:.4f}', f'{item["mean_invested_pct"]:.4f}',
                  f'{item["execution_cost_usd"]:,.2f}'):
        assert value in NUMERIC_TEXT and value in MAIN, value
    assert f'{item["provisional_unpaid_receivable_usd"]:,.2f}' in V2_DIV
for item in CON["results"]:
    assert f'{item["mean_risk_pct"]:.4f}' in TEXT
    assert str(item["days_above_own_budget"]) in RISK
    assert str(item["days_above_fixed_4pct"]) in RISK
assert [r["reference_count"] for r in FIDELITY["dates"]] == [9, 40, 21]
assert all(r["rank_order_equal"] and not r["reference_only"] and not r["stored_only"]
           and r["maximum_common_score_abs_difference"] == 0
           and r["maximum_common_stop_abs_difference"] == 0 for r in FIDELITY["dates"])
assert FIDELITY["flat_first_day"]["reference_target_shares"] == FIDELITY["flat_first_day"]["v5u_next_open_filled_shares"]
for policy in "BC":
    item = next(r for r in TIMING[policy] if r["date"] == "2025-10-23")
    for key in ("close_before_plan_risk_pct", "hypothetical_close_after_next_day_executed_sells_pct",
                "next_open_after_actual_fills_risk_pct", "next_close_risk_pct"):
        assert f'{item[key]:.4f}' in TEXT
for target in re.findall(r"\]\(([^)]+)\)", TEXT):
    if target.startswith(("http://", "https://")):
        continue
    assert (PAPER / target).exists(), target
figure = PAPER / "figures/v2/fig01_timing.svg"
ET.parse(figure)
figure_text = figure.read_text()
assert all(label in figure_text for label in ("23 October 2025", "B fixed 4%", "C dynamic budget", "T+1 open, filled"))
for old_figure in ("fig01_nav.svg", "fig02_drawdown.svg", "fig03_planned_risk.svg", "fig04_fixed_reference.svg"):
    plot = (PAPER / "figures" / old_figure).read_text()
    assert "V5-U" in plot and "2025-09-18" in plot and "2026-10-30" in plot
bib = (PAPER / "references_v2.bib").read_text()
keys = re.findall(r"^@\w+\{([^,]+),", bib, re.M)
assert len(keys) == len(set(keys)) == 8
assert "BaileyBorweinLopezZhu2017" in keys and "10.21314/jcf.2016.322" in bib
assert "2015 author-hosted" not in TEXT
assert "[CITATION NEEDED]" in TEXT
for heading in ("Abstract", "Introduction", "Related literature", "Data and methodology", "Empirical results",
                "Discussion", "Limitations", "Conclusion", "References"):
    assert heading.lower() in TEXT.lower()
assert "282 independent" not in TEXT.lower()
print("V2 numerical source values, timing, sampled fidelity, links, SVG, bibliography and structure PASS")
