"""Generate V5-U paper figures/tables from immutable local research outputs."""

import csv
import html
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "audit"
FIG = ROOT / "paper/figures"
TAB = ROOT / "paper/tables"
SOURCE = Path.home() / "FMA_Independent_Research/audit"
BUNDLE = (Path.home() / "FMA_Competition/Market_Refresh_Runs"
          / "manual_full_20261031T061137Z_432cf6e9/market_bundle")
sys.path.insert(0, str(ROOT / "src"))
from portfolio.provider_actions import index_actions, checked_dividend_amount

COLORS = {"A": "#175e83", "B": "#b35b2d", "C": "#5b4f9b"}
LABELS = {"A": "A baseline", "B": "B fixed 4%", "C": "C dynamic 2–5%"}


def read(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def esc(value):
    return html.escape(str(value))


def tick_label(value):
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:g}"


def svg_line_chart(filename, title, subtitle, series, *, ymin, ymax, ticks, ylabel, horizontal=None, overlays=None):
    width, height = 900, 460
    left, right, top, bottom = 80, 25, 62, 77
    pw, ph = width-left-right, height-top-bottom
    count = len(next(iter(series.values())))
    def x(i): return left + pw*i/(count-1)
    def y(v): return top + ph*(ymax-v)/(ymax-ymin)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#ffffff"/>',
             f'<text x="{left}" y="28" font-family="DejaVu Sans,sans-serif" font-size="18" font-weight="700" fill="#162634">{esc(title)}</text>',
             f'<text x="{left}" y="48" font-family="DejaVu Sans,sans-serif" font-size="11" fill="#536372">{esc(subtitle)}</text>']
    for tick in ticks:
        yy=y(tick)
        parts.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#e2e8ed"/>')
        parts.append(f'<text x="{left-9}" y="{yy+4:.1f}" text-anchor="end" font-family="DejaVu Sans,sans-serif" font-size="11" fill="#536372">{tick_label(tick)}</text>')
    for i,label,anchor in [(0,"2025-09-18","start"),(count//2,"midpoint","middle"),(count-1,"2026-10-30","end")]:
        parts.append(f'<text x="{x(i):.1f}" y="{height-48}" text-anchor="{anchor}" font-family="DejaVu Sans,sans-serif" font-size="11" fill="#536372">{label}</text>')
    if horizontal is not None:
        yy=y(horizontal)
        parts.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#4c5963" stroke-width="1.4" stroke-dasharray="5 4"/>')
    for policy, values in series.items():
        assert len(values)==count and all(math.isfinite(v) for v in values)
        points=" ".join(f"{x(i):.2f},{y(v):.2f}" for i,v in enumerate(values))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{COLORS[policy]}" stroke-width="2.2" stroke-linejoin="round"/>')
        if overlays is not None:
            other=overlays[policy]
            assert len(other)==count
            dotted=" ".join(f"{x(i):.2f},{y(v):.2f}" for i,v in enumerate(other))
            parts.append(f'<polyline points="{dotted}" fill="none" stroke="{COLORS[policy]}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    parts.append(f'<text x="20" y="{top+ph/2:.1f}" transform="rotate(-90 20 {top+ph/2:.1f})" text-anchor="middle" font-family="DejaVu Sans,sans-serif" font-size="11" fill="#536372">{esc(ylabel)}</text>')
    for j,policy in enumerate(series):
        xx=left+j*245
        parts.append(f'<line x1="{xx}" y1="{height-17}" x2="{xx+24}" y2="{height-17}" stroke="{COLORS[policy]}" stroke-width="3"/>')
        parts.append(f'<text x="{xx+31}" y="{height-13}" font-family="DejaVu Sans,sans-serif" font-size="11" fill="#162634">{esc(LABELS[policy])}</text>')
    parts.append('</svg>')
    (FIG/filename).write_text("\n".join(parts)+"\n")


def svg_bars(filename, title, subtitle, groups, ylabel, ymax, ticks):
    width,height=900,460
    left,right,top,bottom=80,25,65,85
    pw,ph=width-left-right,height-top-bottom
    def y(v): return top+ph*(ymax-v)/ymax
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="#fff"/>',
           f'<text x="{left}" y="28" font-family="DejaVu Sans,sans-serif" font-size="18" font-weight="700" fill="#162634">{esc(title)}</text>',
           f'<text x="{left}" y="48" font-family="DejaVu Sans,sans-serif" font-size="11" fill="#536372">{esc(subtitle)}</text>']
    for tick in ticks:
        yy=y(tick)
        parts.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#e2e8ed"/>')
        parts.append(f'<text x="{left-9}" y="{yy+4:.1f}" text-anchor="end" font-family="DejaVu Sans,sans-serif" font-size="11" fill="#536372">{tick_label(tick)}</text>')
    ng=len(groups)
    for gi,(label,values) in enumerate(groups):
        center=left+pw*(gi+0.5)/ng
        for pi,policy in enumerate("ABC"):
            val=values[policy]
            xx=center+(pi-1)*52-19
            yy=y(val)
            parts.append(f'<rect x="{xx:.1f}" y="{yy:.1f}" width="38" height="{top+ph-yy:.1f}" fill="{COLORS[policy]}"/>')
            parts.append(f'<text x="{xx+19:.1f}" y="{yy-6:.1f}" text-anchor="middle" font-family="DejaVu Sans,sans-serif" font-size="10" fill="#162634">{tick_label(val)}</text>')
        parts.append(f'<text x="{center:.1f}" y="{height-50}" text-anchor="middle" font-family="DejaVu Sans,sans-serif" font-size="11" fill="#536372">{esc(label)}</text>')
    parts.append(f'<text x="20" y="{top+ph/2:.1f}" transform="rotate(-90 20 {top+ph/2:.1f})" text-anchor="middle" font-family="DejaVu Sans,sans-serif" font-size="11" fill="#536372">{esc(ylabel)}</text>')
    for j,p in enumerate("ABC"):
        xx=left+j*245
        parts.append(f'<rect x="{xx}" y="{height-21}" width="18" height="10" fill="{COLORS[p]}"/>')
        parts.append(f'<text x="{xx+25}" y="{height-12}" font-family="DejaVu Sans,sans-serif" font-size="11" fill="#162634">{esc(LABELS[p])}</text>')
    parts.append('</svg>')
    (FIG/filename).write_text("\n".join(parts)+"\n")


def risk_paths(daily, trades):
    signals={(r["date"],r["ticker"]):r for r in read(SOURCE/"historical_signal_candidates.csv")}
    actions=index_actions(BUNDLE/"manifest.json")
    cache={}
    def px(ticker, day, adjusted=False):
        key=(ticker,adjusted)
        if key not in cache:
            folder="adjusted" if adjusted else "raw"
            cache[key]={r["Date"]:float(r["Close"]) for r in read(BUNDLE/folder/f"{ticker}.csv")}
        return cache[key][day]
    def dividend(ticker,previous,day):
        ratio=(px(ticker,day,True)/px(ticker,day))/(px(ticker,previous,True)/px(ticker,previous))
        action=actions.get((ticker,day))
        if action and (action["splits"] or action["other"]): raise RuntimeError("UNMODELED_ACTION")
        if abs(ratio-1)<=1e-6: return 0.0
        return float(checked_dividend_amount(action,px(ticker,previous),ratio))
    paths={}
    for policy in "ABC":
        holdings={};previous=None;observations=[]
        by_day=defaultdict(list)
        for trade in trades[policy]:by_day[trade["date"]].append(trade)
        for row in daily[policy]:
            day=row["date"]
            if previous:
                for ticker,p in holdings.items():p["stop"]=max(0.01,p["stop"]-dividend(ticker,previous,day))
            for trade in by_day[day]:
                ticker=trade["ticker"];q=int(trade["shares"])
                if trade["action"]=="BUY":
                    signal=signals[(trade["signal_date"],ticker)]
                    sd=trade["signal_date"]
                    stop=float(signal["planned_stop_adjusted"])*px(ticker,sd)/px(ticker,sd,True)
                    if previous:stop-=dividend(ticker,previous,day)
                    holdings[ticker]={"shares":q,"stop":max(0.01,stop),"sector":signal["sector"]}
                else:
                    holdings[ticker]["shares"]-=q
                    if holdings[ticker]["shares"]==0:del holdings[ticker]
            nav=float(row["nav"]);risk=0;sectors=defaultdict(float)
            for ticker,p in holdings.items():
                close=px(ticker,day)
                risk+=p["shares"]*(max(0,close-p["stop"])+0.01*close)
                sectors[p["sector"]]+=p["shares"]*close
            observations.append({"date":day,"risk_pct":100*risk/nav,
                                 "budget_pct":100*float(row["risk_budget_fraction"]),
                                 "sector_pct":100*max(sectors.values(),default=0)/nav})
            previous=day
        paths[policy]=observations
    return paths


def table(name, caption, headers, body):
    lines=[f"**{caption}**", "", "| "+" | ".join(headers)+" |",
           "| "+" | ".join(["---"]+["---:"]*(len(headers)-1))+" |"]
    lines += ["| "+" | ".join(map(str,row))+" |" for row in body]
    (TAB/name).write_text("\n".join(lines)+"\n")


def main():
    FIG.mkdir(parents=True,exist_ok=True);TAB.mkdir(parents=True,exist_ok=True)
    comparison=json.loads((AUDIT/"p3_abc_v5u_282d_comparison.json").read_text())
    v4=json.loads((AUDIT/"p3_abc_282d_comparison.json").read_text())
    constraints=json.loads((AUDIT/"p3_abc_v5u_282_constraints.json").read_text())
    daily={p:read(AUDIT/f"p3_lifecycle_v5u_{p}_daily.csv") for p in "ABC"}
    trades={p:read(AUDIT/f"p3_lifecycle_v5u_{p}_trades.csv") for p in "ABC"}
    dates=[r["date"] for r in daily["A"]]
    assert len(dates)==282 and dates[0]==comparison["start_date"] and dates[-1]==comparison["end_date"]
    assert all([r["date"] for r in daily[p]]==dates for p in "ABC")
    c={r["policy"]:r for r in constraints["results"]}
    v5={r["policy"]:r for r in comparison["results"]}
    old={r["policy"]:r for r in v4["results"]}
    paths=risk_paths(daily,trades)
    for p in "ABC":
        r=paths[p]
        assert sum(x["risk_pct"]>x["budget_pct"]+1e-7 for x in r)==c[p]["days_above_own_budget"]
        assert sum(x["risk_pct"]>4+1e-7 for x in r)==c[p]["days_above_fixed_4pct"]
        assert sum(x["sector_pct"]>24+1e-7 for x in r)==c[p]["days_above_sector_24pct"]
        assert round(sum(x["risk_pct"] for x in r)/282,4)==c[p]["mean_risk_pct"]
    nav={p:[float(r["nav"]) for r in daily[p]] for p in "ABC"}
    draw={}
    for p in "ABC":
        peak=1_000_000;draw[p]=[]
        for n in nav[p]:peak=max(peak,n);draw[p].append(100*(1-n/peak))
    svg_line_chart("fig01_nav.svg","Cumulative portfolio NAV","V5-U simulated; 282 sessions; NAV axis begins at $900,000",nav,ymin=900000,ymax=1020000,ticks=[900000,930000,960000,990000,1020000],ylabel="US dollars")
    svg_line_chart("fig02_drawdown.svg","Drawdown from running NAV peak","V5-U simulated; initial $1m included in peak",draw,ymin=0,ymax=10,ticks=[0,2,4,6,8,10],ylabel="Drawdown (%)")
    risk={p:[x["risk_pct"] for x in paths[p]] for p in "ABC"}
    budget={p:[x["budget_pct"] for x in paths[p]] for p in "ABC"}
    svg_line_chart("fig03_planned_risk.svg","End-of-day stop-gap exposure versus policy budget","V5-U simulated; solid = observed risk, dashed = own budget",risk,ymin=0,ymax=7,ticks=list(range(8)),ylabel="Risk or budget / NAV (%)",overlays=budget)
    svg_line_chart("fig04_fixed_reference.svg","End-of-day stop-gap exposure versus fixed 4%","V5-U simulated; dashed horizontal line = common 4% reference",risk,ymin=0,ymax=7,ticks=list(range(8)),ylabel="Risk / NAV (%)",horizontal=4)
    svg_line_chart("fig09_policy_budgets.svg","Policy risk budgets","V5-U simulated; A/B fixed 4%; C trailing-SPY budget",budget,ymin=0,ymax=6,ticks=list(range(7)),ylabel="Budget / NAV (%)",horizontal=4)
    invested={p:[100*(float(r["nav"])-float(r["cash"])-float(r["receivable"]))/float(r["nav"]) for r in daily[p]] for p in "ABC"}
    cash={p:[100*float(r["cash"])/float(r["nav"]) for r in daily[p]] for p in "ABC"}
    svg_line_chart("fig05_deployment.svg","Invested fraction through time","V5-U simulated; cash is the complement after receivables, shown in table 2",invested,ymin=0,ymax=100,ticks=[0,20,40,60,80,100],ylabel="Invested / NAV (%)")
    svg_line_chart("fig10_cash.svg","Cash fraction through time","V5-U simulated; dividend receivables are separate from cash",cash,ymin=0,ymax=100,ticks=[0,20,40,60,80,100],ylabel="Cash / NAV (%)")
    svg_bars("fig06_breaches.svg","End-of-day constraint exceedances","V5-U simulated; 282 sessions per policy",[("Own budget",{p:c[p]["days_above_own_budget"] for p in "ABC"}),("Fixed 4%",{p:c[p]["days_above_fixed_4pct"] for p in "ABC"}),("Sector 24%",{p:c[p]["days_above_sector_24pct"] for p in "ABC"})],"Days",180,[0,30,60,90,120,150,180])
    svg_bars("fig07_trades.svg","Transaction counts","V5-U simulated; each buy or sell fill counts once",[("Fills",{p:len(trades[p]) for p in "ABC"})],"Fills",520,[0,100,200,300,400,500])
    svg_bars("fig08_costs.svg","Modeled execution costs","V5-U simulated; $10 per fill plus 5 bps adverse slippage",[("Cost (USD)",{p:round(v5[p]["execution_cost_usd"]) for p in "ABC"})],"US dollars",16000,[0,4000,8000,12000,16000])
    table("table01_policies.md","Table 1. Policy definitions; V5-U uses a nonbinding transaction threshold.",["Policy","New-risk planning","Incumbent trim","Target"],[
        ["A","4%","None","No extra portfolio target"],["B","4%","T-close planned; T+1 sell","Fixed 4%"],["C","Dynamic 2–5%","T-close planned; T+1 sell","4% × clip(σref/σ20, 0.5, 1.25)"]])
    table("table02_main.md","Table 2. V5-U simulated outcomes, 282 sessions; returns include provisional receivables.",["Policy","Final NAV (USD)","Return (%)","Max DD (%)","Mean invested (%)","Mean cash (%)","Fills","Cost (USD)"],[[p,f'{v5[p]["ending_nav_usd"]:,.2f}',f'{v5[p]["total_return_pct"]:.4f}',f'{v5[p]["max_drawdown_pct"]:.4f}',f'{v5[p]["mean_invested_pct"]:.4f}',f'{v5[p]["mean_cash_pct"]:.4f}',len(trades[p]),f'{v5[p]["execution_cost_usd"]:,.2f}'] for p in "ABC"])
    table("table03_constraints.md","Table 3. V5-U end-of-day stop-gap and concentration observations; policy target is not a loss guarantee.",["Policy","Mean risk (%)","Max risk (%)","Own-budget days","Fixed-4% days","Sector-24% days","Name-10% days","Over-14 holdings days","Max own excess (pp)"],[[p,f'{c[p]["mean_risk_pct"]:.4f}',f'{c[p]["max_risk_pct"]:.4f}',c[p]["days_above_own_budget"],c[p]["days_above_fixed_4pct"],c[p]["days_above_sector_24pct"],c[p]["days_above_position_10pct"],c[p]["days_above_14_holdings"],f'{c[p]["max_excess_over_own_budget_pp"]:.4f}'] for p in "ABC"])
    table("table04_regimes.md","Table 4. Distinct V4 contest-capped planning and V5-U cap-neutral regimes.",["Regime","Policy","Final NAV (USD)","Return (%)","Max DD (%)","Fills"],[[reg,p,f'{item[p]["ending_nav_usd"]:,.2f}',f'{item[p]["total_return_pct"]:.4f}',f'{item[p]["max_drawdown_pct"]:.4f}',item[p]["buys"]+item[p]["sells"]] for reg,item in [("V4",old),("V5-U",v5)] for p in "ABC"])
    table("table05_limitations.md","Table 5. Validation scope and data limitations at draft time.",["Issue","Status","Implication"],[
        ["NAV/accounting replay","PASS","Numerical identities; no strategy-performance certification"],["Exit core differential","PASS (408 sampled)","Managed-position targets/reasons only"],["Full signal/order parity","PARTIAL / NOT_TESTED","Conditional implementation fidelity"],["Current-constituent universe","LIMITATION","Survivorship and point-in-time bias"],["Provider-only dividends","PROVISIONAL","NAV includes unsettled receivables"],["Independent untouched period","MISSING","Exploratory, previously inspected sample"]])
    print("Generated 10 SVG figures and 5 Markdown tables; V5-U risk path counts matched source audit")


if __name__=="__main__": main()
