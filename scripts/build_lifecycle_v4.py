"""Create V4 exploratory action-aware experiment runner."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise RuntimeError(
            f"PATCH_ANCHOR_MISMATCH:{source.count(old)}:"
            f"{old[:75]!r}"
        )
    return source.replace(old, new, 1)


source = (
    ROOT / "scripts/run_mpb_lifecycle_v3.py"
).read_text()

source = replace_once(
    source,
    "from collections import defaultdict\n",
    "from collections import defaultdict\n"
    "from decimal import Decimal\n",
)

source = replace_once(
    source,
    "from portfolio.risk_budget import budget_fraction, additional_risk_trim\n",
    "from portfolio.risk_budget import budget_fraction, additional_risk_trim\n"
    "from portfolio.provider_actions import index_actions, checked_dividend_amount\n",
)

source = replace_once(
    source,
    'POLICY_NAME = sys.argv[2].upper() if len(sys.argv) > 2 else "A"\n',
    'POLICY_NAME = sys.argv[2].upper() if len(sys.argv) > 2 else "A"\n'
    'ACTION_MODE = sys.argv[3].upper() if len(sys.argv) > 3 else "STRICT"\n'
    'if ACTION_MODE not in ("STRICT", "PROVIDER_RECONCILED"):\n'
    '    raise ValueError("UNKNOWN_ACTION_MODE")\n',
)

source = replace_once(
    source,
    'EVENTS = load_events(\n'
    '    ROOT / "configs/verified_cash_dividends.json"\n'
    ')\n',
    'EVENTS = load_events(\n'
    '    ROOT / "configs/verified_cash_dividends.json"\n'
    ')\n'
    'ACTION_INDEX = index_actions(BUNDLE / "manifest.json")\n',
)

source = replace_once(
    source,
    "ledger = DividendLedger()\n",
    "ledger = DividendLedger()\n"
    "provisional_claims = {}\n"
    "provisional_events_used = set()\n",
)

source = replace_once(
    source,
    "def mark(day, field):\n",
    'def provisional_total():\n'
    '    return sum(provisional_claims.values(), Decimal("0"))\n'
    '\n'
    'def mark(day, field):\n',
)

source = replace_once(
    source,
    "        + float(ledger.outstanding())\n",
    "        + float(ledger.outstanding())\n"
    "        + float(provisional_total())\n",
)

old_action = '''            if abs(f1 / f0 - 1) <= 1e-6:
                continue

            event = EVENTS.get((ticker, day))
            if (
                event is None
                or event.declared_on > previous_day
                or not factor_reconciles(
                    event, f0, f1,
                    price(ticker, previous_day)
                )
            ):
                raise RuntimeError(
                    "UNVERIFIED_CORPORATE_ACTION:"
                    + ticker + ":" + day
                )

            if ticker in positions:
                p = positions[ticker]
                ledger.accrue(
                    event, day, int(p["shares"])
                )
                p["initial_stop"] = max(
                    0.01,
                    p["initial_stop"] - float(event.amount)
                )

            for o in pending:
                if o["ticker"] == ticker and o["action"] == "BUY":
                    o["stop"] = max(
                        0.01, o["stop"] - float(event.amount)
                    )
'''

new_action = '''            action = ACTION_INDEX.get(
                (ticker, day),
                {"dividends": [], "splits": [], "other": []}
            )

            if action["splits"] or action["other"]:
                raise RuntimeError(
                    "UNSUPPORTED_SPLIT_OR_COMPOSITE_ACTION:"
                    + ticker + ":" + day
                )

            ratio = f1 / f0
            if abs(ratio - 1) <= 1e-6:
                if action["dividends"]:
                    raise RuntimeError(
                        "DIVIDEND_WITHOUT_FACTOR_CHANGE:"
                        + ticker + ":" + day
                    )
                continue

            event = EVENTS.get((ticker, day))
            if event is not None:
                if (
                    event.declared_on > previous_day
                    or not factor_reconciles(
                        event, f0, f1,
                        price(ticker, previous_day)
                    )
                ):
                    raise RuntimeError(
                        "CURATED_DIVIDEND_FACTOR_MISMATCH:"
                        + ticker + ":" + day
                    )
                amount = event.amount
            else:
                if ACTION_MODE != "PROVIDER_RECONCILED":
                    raise RuntimeError(
                        "UNVERIFIED_CORPORATE_ACTION:"
                        + ticker + ":" + day
                    )

                amount = checked_dividend_amount(
                    action,
                    price(ticker, previous_day),
                    ratio,
                )
                provisional_events_used.add((ticker, day))

            if ticker in positions:
                p = positions[ticker]

                if event is not None:
                    ledger.accrue(
                        event, day, int(p["shares"])
                    )
                else:
                    claim_key = (ticker, day)
                    if claim_key in provisional_claims:
                        raise RuntimeError(
                            "DUPLICATE_PROVISIONAL_CLAIM"
                        )
                    provisional_claims[claim_key] = (
                        amount * int(p["shares"])
                    )

                p["initial_stop"] = max(
                    0.01,
                    p["initial_stop"] - float(amount)
                )

            for o in pending:
                if o["ticker"] == ticker and o["action"] == "BUY":
                    o["stop"] = max(
                        0.01, o["stop"] - float(amount)
                    )
'''

source = replace_once(source, old_action, new_action)

source = replace_once(
    source,
    '"receivable": float(ledger.outstanding()),',
    '"receivable": float(ledger.outstanding() + provisional_total()),',
)

source = replace_once(
    source,
    '"dividend_receivable": str(ledger.outstanding()),',
    '"dividend_receivable": str(ledger.outstanding() + provisional_total()),\n'
    '    "provisional_unpaid_receivable": str(provisional_total()),\n'
    '    "provisional_event_count": len(provisional_events_used),\n'
    '    "provisional_events": sorted(\n'
    '        {"ticker": t, "ex_date": d}\n'
    '        for t, d in provisional_events_used\n'
    '    ),',
)

source = replace_once(
    source,
    '"policy": POLICY_NAME,',
    '"policy": POLICY_NAME,\n'
    '    "action_mode": ACTION_MODE,\n'
    '    "provider_only_payment_policy": '
    '"UNSETTLED_RECEIVABLE_NO_CASH_CREDIT",',
)

source = replace_once(
    source,
    '"schema": "FMA_MPB_LIFECYCLE_V3",',
    '"schema": "FMA_MPB_LIFECYCLE_V4",',
)

if "p3_lifecycle_v3_" not in source:
    raise RuntimeError("MISSING_V3_OUTPUT_PATHS")

source = source.replace(
    "p3_lifecycle_v3_", "p3_lifecycle_v4_"
)

# Some earlier V3 versions printed V2 filenames.
source = source.replace(
    'print("Daily:", OUT / "p3_lifecycle_v2_daily.csv")',
    'print("Daily:", OUT / f"p3_lifecycle_v4_{POLICY_NAME}_daily.csv")'
)
source = source.replace(
    'print("Trades:", OUT / "p3_lifecycle_v2_trades.csv")',
    'print("Trades:", OUT / f"p3_lifecycle_v4_{POLICY_NAME}_trades.csv")'
)

target = ROOT / "scripts/run_mpb_lifecycle_v4.py"

if target.exists() and target.read_text() != source:
    raise RuntimeError("V4_RUNNER_EXISTS_WITH_DIFFERENT_CONTENT")

target.write_text(source)

# Build a separate V4 independent accounting replay.
audit = (
    ROOT / "scripts/audit_lifecycle_v3.py"
).read_text()

audit = audit.replace(
    "p3_lifecycle_v3_", "p3_lifecycle_v4_"
)

audit = replace_once(
    audit,
    '''events = json.loads(
    (ROOT / "configs/verified_cash_dividends.json").read_text()
)
''',
    '''events = json.loads(
    (ROOT / "configs/verified_cash_dividends.json").read_text()
)

if run_summary["action_mode"] == "PROVIDER_RECONCILED":
    sys.path.insert(0, str(ROOT / "src"))
    from portfolio.provider_actions import index_actions

    index = index_actions(BUNDLE / "manifest.json")
    curated_keys = {
        (e["ticker"], e["ex_date"]) for e in events
    }

    for (ticker, ex_date), action in index.items():
        if (ticker, ex_date) in curated_keys:
            continue
        if (
            len(action["dividends"]) == 1
            and not action["splits"]
            and not action["other"]
        ):
            events.append({
                "ticker": ticker,
                "ex_date": ex_date,
                "amount_per_share": str(
                    action["dividends"][0]
                ),
                "pay_date": None,
                "status": "PROVIDER_RECONCILED_UNVERIFIED",
            })
''',
)

audit = replace_once(
    audit,
    'and day >= event["pay_date"]',
    'and event["pay_date"] is not None\n'
    '            and day >= event["pay_date"]',
)

audit = replace_once(
    audit,
    '"schema": "FMA_INDEPENDENT_LIFECYCLE_AUDIT_V1",',
    '"schema": "FMA_INDEPENDENT_LIFECYCLE_AUDIT_V4",\n'
    '    "action_mode": run_summary["action_mode"],',
)

audit_target = ROOT / "scripts/audit_lifecycle_v4.py"

if (
    audit_target.exists()
    and audit_target.read_text() != audit
):
    raise RuntimeError(
        "V4_AUDITOR_EXISTS_WITH_DIFFERENT_CONTENT"
    )

audit_target.write_text(audit)

print("=== V4 ACTION-AWARE BUILD ===")
print("STATUS: PASS")
print("V2/V3: UNMODIFIED")
print("RUNNER:", target)
print("AUDITOR:", audit_target)
