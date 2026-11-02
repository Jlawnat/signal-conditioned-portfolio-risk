"""Build V3 policy runner from audited V2.

Fail closed if V2 source layout has changed.
Never modify frozen FMA or the original V2 runner.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source_path = ROOT / "scripts/run_mpb_lifecycle_v2.py"
target_path = ROOT / "scripts/run_mpb_lifecycle_v3.py"

source = source_path.read_text()

def replace_once(old, new):
    global source
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"PATCH_ANCHOR_MISMATCH:{count}:{old[:90]!r}"
        )
    source = source.replace(old, new, 1)

replace_once(
    "from portfolio.exit_policy import ExitParameters, plan_mpb_exit\n",
    "from portfolio.exit_policy import ExitParameters, plan_mpb_exit\n"
    "from portfolio.risk_budget import budget_fraction, additional_risk_trim\n",
)

replace_once(
    "SESSIONS = int(sys.argv[1]) if len(sys.argv) > 1 else 12\n",
    "SESSIONS = int(sys.argv[1]) if len(sys.argv) > 1 else 12\n"
    'POLICY_NAME = sys.argv[2].upper() if len(sys.argv) > 2 else "A"\n'
    'if POLICY_NAME not in ("A", "B", "C"):\n'
    '    raise ValueError("UNKNOWN_POLICY")\n'
    'if POLICY_NAME == "A" and abs(CFG.portfolio_planned_risk_cap - 0.04) > 1e-12:\n'
    '    raise RuntimeError("BASELINE_RISK_CONFIG_MISMATCH")\n',
)

replace_once(
    "spy_calendar = [",
    '''# Pre-study reference volatility: no information from the test period.
VOL20 = None
SIGMA_REFERENCE = None

if POLICY_NAME == "C":
    spy_adjusted = panel("SPY", "adjusted")["Close"]
    VOL20 = (
        spy_adjusted.pct_change()
        .rolling(window=20, min_periods=20)
        .std(ddof=1) * math.sqrt(252)
    )
    reference_sample = VOL20.loc[
        "2025-01-02":"2025-08-29"
    ].dropna()

    if reference_sample.empty:
        raise RuntimeError("MISSING_PRE_STUDY_VOLATILITY")

    SIGMA_REFERENCE = float(reference_sample.median())
    if not math.isfinite(SIGMA_REFERENCE) or SIGMA_REFERENCE <= 0:
        raise RuntimeError("INVALID_REFERENCE_VOLATILITY")

spy_calendar = [''',
)

replace_once(
    "plans_count = 0\n",
    "plans_count = 0\n"
    "overlay_trim_events = 0\n"
    "overlay_trim_shares = 0\n",
)

replace_once(
    '''        # At the close, plan future orders using only
        # information available through this date.
        if day != days[-1]:
''',
    '''        # Risk budget for this day's close; historical trailing data only.
        current_risk_budget = budget_fraction(
            POLICY_NAME,
            sigma_20=(
                float(VOL20.loc[pd.Timestamp(day)])
                if POLICY_NAME == "C" else None
            ),
            sigma_reference=SIGMA_REFERENCE,
        )
        daily[-1]["risk_budget_fraction"] = current_risk_budget

        # At the close, plan future orders using only
        # information available through this date.
        if day != days[-1]:
''',
)

replace_once(
    '''                if result.sell_shares > 0:
                    pending.append({
                        "action": "SELL",
                        "signal_date": day,
                        "ticker": ticker,
                        "shares": result.sell_shares,
                        "reason": result.reason,
                    })

            projected_cash = cash
''',
    '''                if result.sell_shares > 0:
                    pending.append({
                        "action": "SELL",
                        "signal_date": day,
                        "ticker": ticker,
                        "shares": result.sell_shares,
                        "reason": result.reason,
                    })

            # Independent overlay: never modify original MPB exits.
            # Merge extra reductions into existing SELL orders so
            # each ticker has at most one next-open order.
            if POLICY_NAME in ("B", "C"):
                mpb_sells = {
                    o["ticker"]: int(o["shares"])
                    for o in pending
                    if o["action"] == "SELL"
                }

                overlay_result = additional_risk_trim(
                    {
                        ticker: {
                            "shares": int(p["shares"]),
                            "stop": float(p["initial_stop"]),
                        }
                        for ticker, p in positions.items()
                    },
                    mpb_sells,
                    prices={
                        ticker: price(ticker, day)
                        for ticker in positions
                    },
                    nav=nav,
                    risk_fraction=current_risk_budget,
                    gap_buffer=CFG.gap_buffer,
                )

                if not overlay_result["projected_within_budget"]:
                    raise RuntimeError("OVERLAY_TRIM_CANNOT_REACH_TARGET")

                for ticker, extra_qty in sorted(
                    overlay_result["extra_sells"].items()
                ):
                    if extra_qty <= 0:
                        continue

                    existing = next(
                        (
                            o for o in pending
                            if o["action"] == "SELL"
                            and o["ticker"] == ticker
                        ),
                        None,
                    )

                    if existing is None:
                        if len(trades) + len(pending) >= (
                            CONTEST.transaction_limit
                            - STRAT.reserve_transactions
                        ):
                            raise RuntimeError(
                                "OVERLAY_TRANSACTION_CAP_REACHED"
                            )

                        pending.append({
                            "action": "SELL",
                            "signal_date": day,
                            "ticker": ticker,
                            "shares": extra_qty,
                            "reason": "risk_budget_overlay",
                        })
                    else:
                        existing["shares"] += extra_qty
                        existing["reason"] += "|risk_budget_overlay"

                    combined = sum(
                        int(o["shares"]) for o in pending
                        if o["ticker"] == ticker
                        and o["action"] == "SELL"
                    )

                    if combined > int(positions[ticker]["shares"]):
                        raise RuntimeError("OVERLAY_OVERSELL")

                    overlay_trim_events += 1
                    overlay_trim_shares += extra_qty

            projected_cash = cash
''',
)

replace_once(
    '''CFG.portfolio_planned_risk_cap * nav
                        - projected_risk,''',
    '''current_risk_budget * nav
                        - projected_risk,''',
)

replace_once(
    'write_csv("p3_lifecycle_v2_daily.csv", daily)',
    'write_csv(f"p3_lifecycle_v3_{POLICY_NAME}_daily.csv", daily)',
)
replace_once(
    'write_csv("p3_lifecycle_v2_trades.csv", trades)',
    'write_csv(f"p3_lifecycle_v3_{POLICY_NAME}_trades.csv", trades)',
)
replace_once(
    '"schema": "FMA_MPB_LIFECYCLE_V2",',
    '"schema": "FMA_MPB_LIFECYCLE_V3",\n'
    '    "policy": POLICY_NAME,\n'
    '    "sigma_reference": SIGMA_REFERENCE,\n'
    '    "overlay_trim_events_planned": overlay_trim_events,\n'
    '    "overlay_trim_shares_planned": overlay_trim_shares,',
)
replace_once(
    'OUT / "p3_lifecycle_v2_summary.json"',
    'OUT / f"p3_lifecycle_v3_{POLICY_NAME}_summary.json"',
)
replace_once(
    'print("=== MPB MULTI-ASSET LIFECYCLE V2 ===")',
    'print("=== MPB MULTI-ASSET LIFECYCLE V3 ===")',
)

if target_path.exists() and target_path.read_text() != source:
    raise RuntimeError(
        "V3_ALREADY_EXISTS_WITH_DIFFERENT_CONTENT"
    )

target_path.write_text(source)

# Produce policy-specific independent replay auditor.
audit_source = (
    ROOT / "scripts/audit_lifecycle_v2.py"
).read_text()

def audit_replace(old, new):
    global audit_source
    if audit_source.count(old) != 1:
        raise RuntimeError(
            f"AUDIT_PATCH_ANCHOR_MISMATCH:{old[:70]!r}"
        )
    audit_source = audit_source.replace(old, new, 1)

audit_replace(
    "import math\n",
    "import math\nimport sys\n",
)
audit_replace(
    "ROOT = Path(__file__).resolve().parents[1]\n",
    'ROOT = Path(__file__).resolve().parents[1]\n'
    'POLICY_NAME = sys.argv[1].upper() if len(sys.argv) > 1 else "A"\n'
    'if POLICY_NAME not in ("A", "B", "C"):\n'
    '    raise ValueError("UNKNOWN_POLICY")\n',
)
audit_replace(
    'AUDIT = ROOT / "audit"\n',
    '''AUDIT = ROOT / "audit"

run_summary = json.loads(
    (AUDIT / f"p3_lifecycle_v3_{POLICY_NAME}_summary.json").read_text()
)
if (
    run_summary["status"] != "PASS"
    or run_summary["sessions_completed"]
       != run_summary["sessions_requested"]
):
    raise RuntimeError("REFUSE_INCOMPLETE_RUN_AUDIT")
''',
)
audit_replace(
    'AUDIT / "p3_lifecycle_v2_daily.csv"',
    'AUDIT / f"p3_lifecycle_v3_{POLICY_NAME}_daily.csv"',
)
audit_replace(
    'AUDIT / "p3_lifecycle_v2_trades.csv"',
    'AUDIT / f"p3_lifecycle_v3_{POLICY_NAME}_trades.csv"',
)
audit_replace(
    'AUDIT / "p3_lifecycle_v2_independent_audit.json"',
    'AUDIT / f"p3_lifecycle_v3_{POLICY_NAME}_independent_audit.json"',
)

audit_target = ROOT / "scripts/audit_lifecycle_v3.py"

if (
    audit_target.exists()
    and audit_target.read_text() != audit_source
):
    raise RuntimeError(
        "V3_AUDITOR_ALREADY_EXISTS_WITH_DIFFERENT_CONTENT"
    )

audit_target.write_text(audit_source)

print("=== V3 BUILD ===")
print("STATUS: PASS")
print("RUNNER:", target_path)
print("AUDITOR:", audit_target)
print("V2 SOURCE: UNMODIFIED")
