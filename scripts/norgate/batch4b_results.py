"""Postprocess completed, approved NG-SF-270-LW official journals.

This is an analysis and audit consumer. It does not alter the approved runner.
Outputs are kept in the ignored private directory.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "norgate"))
from run_ng_sf_270_lw_v1 import approved, code_manifest_hash, sha256
from reconcile_ng_sf_diagnostic_v1 import audit


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def write_csv(path, data):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def describe(values):
    a = np.asarray(values, dtype=float)
    if not len(a):
        return {"n": 0, "mean": None, "median": None, "p05": None, "p95": None, "min": None, "max": None}
    return {"n": len(a), "mean": float(a.mean()), "median": float(np.median(a)),
            "p05": float(np.percentile(a, 5)), "p95": float(np.percentile(a, 95)),
            "min": float(a.min()), "max": float(a.max())}


def block_interval(diff, length, seed=20261102, replicates=10000):
    x = np.asarray(diff, dtype=float)
    n = len(x)
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n, size=(replicates, math.ceil(n / length)))
    offsets = np.arange(length)
    indices = (starts[:, :, None] + offsets) % n
    means = x[indices.reshape(replicates, -1)[:, :n]].mean(axis=1)
    return {"block_length": length, "replicates": replicates, "seed": seed,
            "rng": "numpy.default_rng (PCG64)", "lower": float(np.percentile(means, 2.5)),
            "upper": float(np.percentile(means, 97.5)),
            "replicate_mean_sha256": hashlib.sha256(means.tobytes()).hexdigest()}


def drawdown(nav):
    peak = np.maximum.accumulate(nav)
    return float(np.min(nav / peak - 1))


def svg_lines(path, daily):
    colors = {"A": "#303f9f", "B": "#b53b35", "C": "#157a64", "F": "#a35f0a"}
    width, height, left, top, right, bottom = 960, 500, 70, 30, 30, 55
    all_nav = [r["nav"] for d in daily.values() for r in d]
    lo, hi = min(all_nav), max(all_nav)
    span = hi - lo or 1
    paths = []
    for policy, data in daily.items():
        points = []
        for i, row in enumerate(data):
            x = left + i * (width-left-right)/(len(data)-1)
            y = height-bottom-(row["nav"]-lo)/span*(height-top-bottom)
            points.append(f"{x:.2f},{y:.2f}")
        paths.append(f'<polyline fill="none" stroke="{colors[policy]}" stroke-width="2" points="{" ".join(points)}"/>')
    legend = "".join(f'<text x="{left+i*110}" y="20" fill="{colors[p]}" font-size="14">Policy {p}</text>' for i,p in enumerate(daily))
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/><text x="10" y="45" font-size="12">NAV ($)</text><text x="10" y="{height-bottom}" font-size="12">{lo:,.0f}</text><text x="10" y="{top+10}" font-size="12">{hi:,.0f}</text><line x1="{left}" x2="{left}" y1="{top}" y2="{height-bottom}" stroke="#888"/><line x1="{left}" x2="{width-right}" y1="{height-bottom}" y2="{height-bottom}" stroke="#888"/>{legend}{"".join(paths)}<text x="{left}" y="{height-15}" font-size="12">{daily["A"][0]["date"]}</text><text x="{width-right-100}" y="{height-15}" font-size="12">{daily["A"][-1]["date"]}</text></svg>'
    path.write_text(svg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval", default="restricted_norgate/ng_sf_270_lw_approval_v2.json")
    parser.add_argument("--output", default="restricted_norgate/batch4b_official_20261102")
    args = parser.parse_args()
    approval = json.loads(Path(args.approval).read_text())
    db = approval["data_manifest"]["db_path"]
    events = approval["data_manifest"]["event_register_path"]
    approved(args.approval, approval["protocol_path"], db, events)
    assert approval["configuration"]["policy_set"] == ["A", "B", "C", "F"]
    out = Path(args.output)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError("OUTPUT_EXISTS")
    out.mkdir(parents=True)
    data, source_hashes, audits = {}, {}, {}
    base = ROOT / "restricted_norgate/ng_sf_270_lw_v1"
    for policy in ("A", "B", "C", "F"):
        candidates = []
        for p in base.glob("run_*/result_private.json"):
            record = json.loads(p.read_text())
            if record.get("policy") == policy:
                candidates.append(p.parent)
        if len(candidates) != 1:
            raise ValueError(f"OFFICIAL_OUTPUT_COUNT_{policy}:{len(candidates)}")
        directory = candidates[0]
        result = json.loads((directory/"result_private.json").read_text())
        snap, orders, pairs = [rows(directory/(name+".jsonl")) for name in ("snapshots","orders","pairs")]
        if (len(result["daily"]),len(result["pairs"]),len(snap),len(pairs)) != (230,229,1374,229):
            raise ValueError(f"INCOMPLETE_{policy}")
        if result["reconciliation"]["status"] != "PASS":
            raise ValueError(f"ORDER_RECONCILIATION_{policy}")
        # Reuse the separately written arithmetic auditor on a read-only view of
        # the official journal. Its marker only satisfies the diagnostic file API.
        mirror = out/("audit_view_"+policy)
        mirror.mkdir()
        for name in ("snapshots","orders","pairs"):
            (mirror/(name+".jsonl")).symlink_to((directory/(name+".jsonl")).resolve())
        (mirror/"diagnostic_private.json").write_text(json.dumps({
            "status":"NO_AFFECTED_EVENT_FOUND","performance_not_reported":True})+"\n")
        audited = audit(mirror, events, db)
        if audited["status"] != "PASS":
            raise ValueError(f"ACCOUNTING_AUDIT_{policy}")
        audits[policy] = audited
        source_hashes[policy] = {name:sha256(directory/name) for name in
                                 ("result_private.json","snapshots.jsonl","orders.jsonl","pairs.jsonl")}
        data[policy] = {"run_id":directory.name,"result":result,"snapshots":snap,"orders":orders,"pairs":pairs}
    dates = [r["date"] for r in data["A"]["result"]["daily"]]
    if any([r["date"] for r in data[p]["result"]["daily"]] != dates for p in ("B","C","F")):
        raise ValueError("UNPAIRED_CLOSE_DATES")
    if dates[0] != "2025-12-02" or dates[-1] != "2026-10-30" or len(set(dates)) != 230:
        raise ValueError("CALENDAR_MISMATCH")
    daily_rows, policy_metrics, gap_rows, pair_rows, evidence_rows = [], {}, [], [], []
    evidence_by_id = {e["event_id"]:e for e in json.loads(Path(approval["data_manifest"]["event_evidence_path"]).read_text())}
    for event in json.loads(Path(events).read_text()):
        evidence = evidence_by_id[event["event_id"]]
        evidence_rows.append({"event_id":event["event_id"],"ex_date":event.get("ex_date"),
                              "payment_date":event.get("payment_date"),
                              "payment_not_before_date":event.get("payment_not_before_date"),
                              "source_id":event.get("source_id"),
                              "official_issuer_notice":evidence.get("official_issuer_notice"),
                              "ex_date_basis":evidence.get("ex_date_basis"),
                              "evidence_status":evidence.get("evidence_status")})
    for p, bundle in data.items():
        d = bundle["result"]["daily"]
        n = np.array([row["nav"] for row in d])
        risk = np.array([row["marked_stop_gap_exposure"] for row in d])
        budget = np.array([row["risk_budget_fraction"] for row in d])
        cash = np.array([row["cash"] for row in d])
        recv = np.array([row["receivable"] for row in d])
        own_excess = np.maximum(0, risk-budget)
        common_excess = np.maximum(0, risk-.04)
        for row, oe, ce in zip(d,own_excess,common_excess):
            daily_rows.append({"policy":p,**row,"own_budget_excess":float(oe),
                               "common_4pct_excess":float(ce),
                               "invested_fraction_ex_receivable":float((row["nav"]-row["cash"]-row["receivable"])/row["nav"])})
        gaps = bundle["result"]["pairs"]
        pair_rows.extend({"policy":p,**g} for g in gaps)
        snap_by_pair = {}
        for snap in bundle["snapshots"]:
            snap_by_pair.setdefault((snap["decision_date"],snap["execution_date"]),{})[snap["simulation_phase"]] = snap
        open_exceed = close_exceed = persists = 0
        for pair in gaps:
            phases = snap_by_pair[(pair["decision_date"],pair["execution_date"])]
            s4,s5 = phases["S4_POST_FILL"],phases["S5_CLOSE"]
            opening = s4["marked_stop_gap_exposure"] > s4["budget_fraction"] + 1e-9
            closing = s5["marked_stop_gap_exposure"] > s5["budget_fraction"] + 1e-9
            open_exceed += opening
            close_exceed += closing
            persists += opening and closing
        for population, subset in (("all",gaps),("orders",[g for g in gaps if g["had_orders"]]),
                                   ("overlay",[g for g in gaps if g["had_overlay_intervention"]])):
            gap_rows.append({"policy":p,"population":population,"n":len(subset),
                             "missing":0,"crossing_count":sum(g["compliant_to_exceedance"] for g in subset),
                             "signed":describe([g["gap"] for g in subset]),
                             "positive":describe([g["positive_gap"] for g in subset])})
        orders = bundle["orders"]
        filled = [o for o in orders if o["order_state"]=="FILLED"]
        policy_metrics[p] = {"sessions":len(d),"pairs":len(gaps),"initial_nav":float(n[0]),
            "final_nav":float(n[-1]),"cumulative_return":float(n[-1]/n[0]-1),
            "max_drawdown":drawdown(n),"common_4pct_excess_mean":float(common_excess.mean()),
            "own_budget_excess_mean":float(own_excess.mean()),
            "common_4pct_exceedance_days":int(np.count_nonzero(common_excess>1e-9)),
            "own_budget_exceedance_days":int(np.count_nonzero(own_excess>1e-9)),
            "common_4pct_excess_severity":describe(common_excess[common_excess>1e-9]),
            "own_budget_excess_severity":describe(own_excess[own_excess>1e-9]),
            "invested_fraction_ex_receivable":describe([(row["nav"]-row["cash"]-row["receivable"])/row["nav"] for row in d]),
            "spendable_cash":describe(cash),"ending_cash":float(cash[-1]),
            "ending_receivable":float(recv[-1]),"transaction_count":len(filled),
            "buy_count":sum(o["action"]=="BUY" for o in filled),
            "sell_count":sum(o["action"]=="SELL" for o in filled),
            "modeled_costs":float(sum(o["realized_cost"] for o in filled)),
            "opening_own_budget_exceedance_pairs":open_exceed,
            "next_close_own_budget_exceedance_pairs":close_exceed,
            "opening_to_close_persistent_exceedance_pairs":persists,
            "missing_close":sum(not math.isfinite(x) for x in n)+sum(not math.isfinite(x) for x in risk)}
    a = [r for r in daily_rows if r["policy"]=="A"]
    b = [r for r in daily_rows if r["policy"]=="B"]
    diff = np.array([x["common_4pct_excess"]-y["common_4pct_excess"] for x,y in zip(b,a)])
    primary = {"estimate":float(diff.mean()),"unit":"exposure fraction",
               "estimate_percentage_points":float(100*diff.mean()),"paired_days":len(diff),
               "policy_A_mean":policy_metrics["A"]["common_4pct_excess_mean"],
               "policy_B_mean":policy_metrics["B"]["common_4pct_excess_mean"],
               "bootstrap_20":block_interval(diff,20),
               "sensitivity_10":block_interval(diff,10),
               "sensitivity_40":block_interval(diff,40)}
    write_csv(out/"daily_policy.csv",daily_rows)
    write_csv(out/"paired_primary_daily.csv",[{"date":day,"B_minus_A":float(x)} for day,x in zip(dates,diff)])
    write_csv(out/"implementation_pairs.csv",pair_rows)
    write_csv(out/"event_evidence_mapping.csv",evidence_rows)
    write_csv(out/"policy_summary.csv",[{"policy":p,**{k:v for k,v in m.items() if not isinstance(v,dict)}} for p,m in policy_metrics.items()])
    write_csv(out/"gap_summary.csv",[{k:json.dumps(v,sort_keys=True) if isinstance(v,dict) else v for k,v in row.items()} for row in gap_rows])
    svg_lines(out/"nav_paths.svg",{p:data[p]["result"]["daily"] for p in ("A","B","C","F")})
    summary={"status":"PASS","approval_sha256":sha256(args.approval),
             "protocol_sha256":approval["protocol_sha256"],"code_manifest_hash":code_manifest_hash(approval["protocol_path"]),
             "source_hashes":source_hashes,"audit_results":audits,"run_ids":{p:data[p]["run_id"] for p in data},
             "primary_B_minus_A":primary,"policy_metrics":policy_metrics,"implementation_gaps":gap_rows,
             "secondary_descriptive":{"C_minus_B_common_excess":policy_metrics["C"]["common_4pct_excess_mean"]-policy_metrics["B"]["common_4pct_excess_mean"],
                "C_minus_F_common_excess":policy_metrics["C"]["common_4pct_excess_mean"]-policy_metrics["F"]["common_4pct_excess_mean"],
                "C_minus_B_cumulative_return":policy_metrics["C"]["cumulative_return"]-policy_metrics["B"]["cumulative_return"],
                "C_minus_F_cumulative_return":policy_metrics["C"]["cumulative_return"]-policy_metrics["F"]["cumulative_return"]}}
    (out/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    manifest={p.name:sha256(p) for p in sorted(out.iterdir()) if p.is_file()}
    (out/"output_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":"PASS","output":str(out),"primary":primary,"run_ids":summary["run_ids"]}))


if __name__ == "__main__":
    main()
