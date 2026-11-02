"""Read-only integrity check for the frozen paper evidence package."""

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
REPORT = json.loads((AUDIT / "p3_abc_v5u_282d_comparison.json").read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def verify():
    assert REPORT["sessions"] == 282
    assert REPORT["start_date"] == "2025-09-18"
    assert REPORT["end_date"] == "2026-10-30"
    for policy in "ABC":
        prefix = f"p3_lifecycle_v5u_{policy}"
        paths = {
            "summary": AUDIT / f"{prefix}_summary.json",
            "audit": AUDIT / f"{prefix}_independent_audit.json",
            "daily": AUDIT / f"{prefix}_daily.csv",
            "trades": AUDIT / f"{prefix}_trades.csv",
        }
        for kind, path in paths.items():
            assert digest(path) == REPORT["source_sha256"][policy][kind], path
        summary = json.loads(paths["summary"].read_text())
        replay = json.loads(paths["audit"].read_text())
        daily = rows(paths["daily"])
        trades = rows(paths["trades"])
        reported = next(r for r in REPORT["results"] if r["policy"] == policy)
        assert summary["policy"] == policy
        assert summary["status"] == replay["status"] == "PASS"
        assert summary["transaction_cap_scenario"] == "NON_BINDING_RESEARCH_1B"
        assert summary["sessions_completed"] == replay["sessions_replayed"] == 282
        assert len(daily) == 282 and len(trades) == replay["trades_replayed"]
        assert daily[0]["date"] == REPORT["start_date"]
        assert daily[-1]["date"] == REPORT["end_date"]
        nav = [float(r["nav"]) for r in daily]
        peak = 1_000_000.0
        drawdown = 0.0
        for value in nav:
            peak = max(peak, value)
            drawdown = max(drawdown, 100 * (1 - value / peak))
        assert round(nav[-1], 2) == reported["ending_nav_usd"]
        assert round(100 * (nav[-1] / 1_000_000 - 1), 4) == reported["total_return_pct"]
        assert round(drawdown, 4) == reported["max_drawdown_pct"]
        print(f"{policy}: 4 hashes, 282 sessions, {len(trades)} fills, NAV/return/drawdown PASS")

    snapshot = json.loads((ROOT / "configs/mpb_exit_reference.json").read_text())
    frozen = (Path.home() / "FMA_Competition/fma_mpb_v41_20261013/fma_mpb_v41")
    for name, expected in snapshot["source_sha256"].items():
        assert digest(frozen / name) == expected, name
    print("Frozen FMA: 2 source hashes PASS")


if __name__ == "__main__":
    verify()
