"""Read-only Draft V1 artifact and source-value checks."""

import json
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
AUDIT = ROOT / "audit"
section_names = [
    "01_TITLE_ABSTRACT.md", "02_INTRODUCTION.md", "03_LITERATURE_REVIEW.md",
    "04_DATA_METHODOLOGY.md", "05_EMPIRICAL_RESULTS.md", "06_DISCUSSION.md",
    "07_LIMITATIONS.md", "08_CONCLUSION.md",
]
sections = [(PAPER / name).read_text().strip() for name in section_names]
assert (PAPER / "MANUSCRIPT_DRAFT_V1.md").read_text() == "\n\n---\n\n".join(sections) + "\n"

for page in PAPER.glob("*.md"):
    for target in re.findall(r"\]\(([^)]+)\)", page.read_text()):
        if target.startswith(("https://", "http://", "#")):
            continue
        assert (page.parent / target).exists(), (page, target)

comparison = json.loads((AUDIT / "p3_abc_v5u_282d_comparison.json").read_text())
constraints = json.loads((AUDIT / "p3_abc_v5u_282_constraints.json").read_text())
main = (PAPER / "tables/table02_main.md").read_text()
risk = (PAPER / "tables/table03_constraints.md").read_text()
manuscript = (PAPER / "MANUSCRIPT_DRAFT_V1.md").read_text()
for row in comparison["results"]:
    for number in (f'{row["ending_nav_usd"]:,.2f}', f'{row["total_return_pct"]:.4f}',
                   f'{row["max_drawdown_pct"]:.4f}', f'{row["execution_cost_usd"]:,.2f}'):
        assert number in main, number
    assert f'${row["ending_nav_usd"]:,.2f}' in manuscript
for row in constraints["results"]:
    assert str(row["days_above_own_budget"]) in risk
    assert str(row["days_above_fixed_4pct"]) in risk

svg = sorted((PAPER / "figures").glob("fig*.svg"))
png = sorted((PAPER / "figures").glob("fig*.png"))
assert len(svg) == len(png) == 10
for path in svg:
    ET.parse(path)
    preview = path.with_suffix(".png")
    binary = preview.read_bytes()
    assert binary[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", binary[16:24]) == (900, 460)

bib = (PAPER / "references.bib").read_text()
assert len(re.findall(r"^@(article|misc)\{", bib, re.M)) == 8
assert bib.count("url = {https://") == 8
print("Draft V1: 8 sections, 10 SVG/PNG pairs, 5 tables, 8 bibliography entries PASS")
print("Main table and manuscript source-value checks, local links, SVG/PNG validation PASS")
