"""Generate V2 tables and one sampled timing figure from immutable audits."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "audit"
TAB = ROOT / "paper/tables/v2"
FIG = ROOT / "paper/figures/v2"
TAB.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
comparison = {r["policy"]: r for r in json.loads((AUDIT / "p3_abc_v5u_282d_comparison.json").read_text())["results"]}
timing = json.loads((TAB / "risk_timing_sample.json").read_text())
with (Path.home() / "FMA_Independent_Research/audit/historical_signal_candidates.csv").open(newline="") as fh:
    candidates = list(csv.DictReader(fh))
assert len(candidates) == 1229


def table(name, title, headers, body):
    lines = [f"**{title}**", "", "| " + " | ".join(headers) + " |",
             "| " + " | ".join(["---"] + ["---:"] * (len(headers) - 1)) + " |"]
    lines += ["| " + " | ".join(str(x) for x in row) + " |" for row in body]
    (TAB / name).write_text("\n".join(lines) + "\n")


selected = [("B", "2025-10-23"), ("C", "2025-10-23"),
            ("B", "2026-06-04"), ("C", "2026-01-05")]
rows = []
for policy, date in selected:
    item = next(r for r in timing[policy] if r["date"] == date)
    rows.append([policy, date, *[f"{item[k]:.4f}" for k in (
        "budget_pct", "close_before_plan_risk_pct",
        "hypothetical_close_after_next_day_executed_sells_pct",
        "next_open_after_actual_fills_risk_pct", "next_close_risk_pct")]])
table("table01_risk_timing.md",
      "V2 Table 1. Selected V5-U own-budget breach transitions (% of NAV). Planned-sell state is hypothetical at T prices; T+1 states use simulated fills. Not a full-history cause decomposition.",
      ["Policy", "T close", "T budget", "Before plan", "Hypothetical after sells", "T+1 post-fill open", "T+1 close"], rows)

table("table02_deployment.md",
      "V2 Table 2. V5-U deployment level and modeled frictions, 282 sessions. Candidate events (1,229 total) precede portfolio feasibility checks and are shared across policies.",
      ["Policy", "Mean invested %", "Mean cash %", "Fills", "Modeled cost USD", "Shared candidate events"],
      [[p, f'{comparison[p]["mean_invested_pct"]:.4f}', f'{comparison[p]["mean_cash_pct"]:.4f}',
        comparison[p]["buys"] + comparison[p]["sells"], f'{comparison[p]["execution_cost_usd"]:,.2f}',
        len(candidates)] for p in "ABC"])

events = json.loads((ROOT / "configs/verified_cash_dividends.json").read_text())
curated = {}
for policy in "ABC":
    with (AUDIT / f"p3_lifecycle_v5u_{policy}_trades.csv").open(newline="") as fh:
        trades = list(csv.DictReader(fh))
    holdings = {}
    accrual = 0.0
    for day in sorted({t["date"] for t in trades} | {e["ex_date"] for e in events}):
        for event in events:
            if event["ex_date"] == day:
                accrual += holdings.get(event["ticker"], 0) * float(event["amount_per_share"])
        for trade in (t for t in trades if t["date"] == day):
            change = int(trade["shares"]) * (1 if trade["action"] == "BUY" else -1)
            holdings[trade["ticker"]] = holdings.get(trade["ticker"], 0) + change
    curated[policy] = accrual
assert {p: round(v, 2) for p, v in curated.items()} == {"A": 404.63, "B": 490.70, "C": 489.19}
table("table03_dividends.md",
      "V2 Table 3. V5-U dividend accrual classes and narrow endpoint NAV component sensitivity (USD). Subtraction does not recompute the trading path.",
      ["Policy", "Curated accrual", "Provisional unpaid", "Combined accrual", "Reported NAV", "NAV minus endpoint provisional"],
      [[p, f'{curated[p]:,.2f}', f'{comparison[p]["provisional_unpaid_receivable_usd"]:,.2f}',
        f'{curated[p]+comparison[p]["provisional_unpaid_receivable_usd"]:,.2f}',
        f'{comparison[p]["ending_nav_usd"]:,.2f}',
        f'{comparison[p]["ending_nav_usd"]-comparison[p]["provisional_unpaid_receivable_usd"]:,.2f}']
       for p in "ABC"])

# One focused plot. The second point is a hypothetical T-price state, clearly
# distinguished from the actual next-open and next-close observations.
stage_keys = ["close_before_plan_risk_pct",
              "hypothetical_close_after_next_day_executed_sells_pct",
              "next_open_after_actual_fills_risk_pct", "next_close_risk_pct"]
labels = ["T close", "T close, hypothetical", "T+1 open, filled", "T+1 close"]
items = {p: next(r for r in timing[p] if r["date"] == "2025-10-23") for p in "BC"}
width, height = 820, 420
left, right, top, bottom = 86, 25, 65, 96
plot_w, plot_h = width-left-right, height-top-bottom
xs = [left + plot_w*i/3 for i in range(4)]
def y(v): return top + plot_h*(7-v)/7
parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
         '<rect width="100%" height="100%" fill="white"/>',
         '<text x="86" y="27" font-family="sans-serif" font-size="17" font-weight="bold">Selected budget-breach transition</text>',
         '<text x="86" y="47" font-family="sans-serif" font-size="11">V5-U, 23 October 2025; T-close hypothetical state is not an executed portfolio</text>']
for tick in range(8):
    yy = y(tick)
    parts += [f'<line x1="{left}" x2="{width-right}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="#e2e8ed"/>',
              f'<text x="{left-10}" y="{yy+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="11">{tick}%</text>']
for i, label in enumerate(labels):
    parts.append(f'<text x="{xs[i]:.1f}" y="{height-55}" text-anchor="middle" font-family="sans-serif" font-size="11">{label}</text>')
for policy, color in [("B", "#b35b2d"), ("C", "#5b4f9b")]:
    values = [items[policy][k] for k in stage_keys]
    points = " ".join(f"{x:.1f},{y(v):.1f}" for x, v in zip(xs, values))
    parts.append(f'<polyline points="{points}" stroke="{color}" stroke-width="2.5" fill="none"/>')
    for x, v in zip(xs, values):
        parts.append(f'<circle cx="{x:.1f}" cy="{y(v):.1f}" r="4" fill="{color}"/>')
    yy = y(items[policy]["budget_pct"])
    parts.append(f'<line x1="{left}" x2="{width-right}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="{color}" stroke-dasharray="5 4" opacity=".65"/>')
    parts.append(f'<text x="{width-right-3}" y="{yy-5:.1f}" text-anchor="end" font-family="sans-serif" font-size="10" fill="{color}">{policy} target {items[policy]["budget_pct"]:.2f}%</text>')
parts += ['<text x="20" y="186" transform="rotate(-90 20 186)" text-anchor="middle" font-family="sans-serif" font-size="11">Stop-gap risk / NAV (%)</text>',
          '<text x="86" y="400" font-family="sans-serif" font-size="11" fill="#b35b2d">● B fixed 4%</text>',
          '<text x="230" y="400" font-family="sans-serif" font-size="11" fill="#5b4f9b">● C dynamic budget</text>',
          '</svg>']
(FIG / "fig01_timing.svg").write_text("\n".join(parts) + "\n")
print("V2: 3 tables, 1 SVG; source audit values reconciled")
