"""Historical multi-asset MPB lifecycle integration pilot.

Research software validation, not final strategy backtest.
Frozen FMA is used read-only for reference feature generation.
"""

import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE_AUDIT = Path.home() / "FMA_Independent_Research/audit"
BUNDLE = (
    Path.home()
    / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)
FMA = (
    Path.home()
    / "FMA_Competition/fma_mpb_v41_20261013"
    / "fma_mpb_v41"
)

sys.path.insert(0, str(ROOT / "src"))
from portfolio.exit_policy import ExitParameters, plan_mpb_exit
from portfolio.risk_budget import budget_fraction, additional_risk_trim
from portfolio.provider_actions import index_actions, checked_dividend_amount
from portfolio.corporate_actions import (
    DividendLedger, load_events, factor_reconciles
)
from portfolio.decision_execution_log_v1 import (
    LocalJournal, exposure, projected_positions, stable_id, implementation_gap,
    reconcile_directory
)

snapshot = json.loads(
    (ROOT / "configs/mpb_exit_reference.json").read_text()
)
for filename, expected in snapshot["source_sha256"].items():
    actual = hashlib.sha256(
        (FMA / filename).read_bytes()
    ).hexdigest()
    if actual != expected:
        raise RuntimeError("FROZEN_SOURCE_HASH_MISMATCH")

sys.path.insert(0, str(FMA))
import momentum_pullback_breakout as reference
from config import CONTEST, STRAT

CFG = reference.CFG
POLICY = ExitParameters.from_json(
    ROOT / "configs/mpb_exit_reference.json"
)
EVENTS = load_events(
    ROOT / "configs/verified_cash_dividends.json"
)
ACTION_INDEX = index_actions(BUNDLE / "manifest.json")
CONFIG_HASH = hashlib.sha256(
    (FMA / "config.py").read_bytes()
    + json.dumps(snapshot, sort_keys=True).encode()
    + b"V5U_LOGGED_V1"
).hexdigest()
MANIFEST_HASH = hashlib.sha256(
    b"".join(hashlib.sha256(path.read_bytes()).digest() for path in (
        BUNDLE / "manifest.json",
        SOURCE_AUDIT / "historical_signal_candidates.csv",
        ROOT / "configs/verified_cash_dividends.json",
    ))
).hexdigest()

START_CASH = 1_000_000.0
SLIP = STRAT.assumed_slippage_bps / 10000
FEE = float(CONTEST.commission_per_trade)
SESSIONS = int(sys.argv[1]) if len(sys.argv) > 1 else 12
POLICY_NAME = sys.argv[2].upper() if len(sys.argv) > 2 else "A"
ACTION_MODE = sys.argv[3].upper() if len(sys.argv) > 3 else "STRICT"
if ACTION_MODE not in ("STRICT", "PROVIDER_RECONCILED"):
    raise ValueError("UNKNOWN_ACTION_MODE")
if POLICY_NAME not in ("A", "B", "C"):
    raise ValueError("UNKNOWN_POLICY")
if POLICY_NAME == "A" and abs(CFG.portfolio_planned_risk_cap - 0.04) > 1e-12:
    raise RuntimeError("BASELINE_RISK_CONFIG_MISMATCH")

assert 1 <= SESSIONS <= 282

def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))

signals = read_csv(
    SOURCE_AUDIT / "historical_signal_candidates.csv"
)
assert len(signals) == 1229

by_day = defaultdict(list)
for s in signals:
    by_day[s["date"]].append(s)

for records in by_day.values():
    records.sort(
        key=lambda s: (-float(s["score"]), s["ticker"])
    )

cache = {}

def panel(ticker, kind):
    key = (ticker, kind)
    if key not in cache:
        path = BUNDLE / kind / f"{ticker}.csv"
        df = pd.read_csv(path, parse_dates=["Date"])
        df = df.set_index("Date").sort_index()
        if df.index.has_duplicates:
            raise RuntimeError("DUPLICATE_PANEL_DATES")
        cols = ["Open", "High", "Low", "Close", "Volume"]
        cache[key] = df[cols].astype(float)
    return cache[key]

def price(ticker, day, field="Close", kind="raw"):
    v = float(panel(ticker, kind).at[pd.Timestamp(day), field])
    if not math.isfinite(v) or v <= 0:
        raise RuntimeError("INVALID_PRICE:" + ticker + ":" + day)
    return v

def factor(ticker, day):
    return (
        price(ticker, day, kind="adjusted")
        / price(ticker, day)
    )

def features(ticker, day):
    asof = pd.Timestamp(day)

    # Physically truncate both panels to prohibit future
    # observations from entering the feature calculation.
    stock = panel(ticker, "adjusted").loc[:asof]
    spy = panel("SPY", "adjusted").loc[:asof]
    return reference.signal_features(stock, spy, asof)

# Pre-study reference volatility: no information from the test period.
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

spy_calendar = [
    t.strftime("%Y-%m-%d")
    for t in panel("SPY", "raw").index
]
start = spy_calendar.index("2025-09-18")
days = spy_calendar[start:start + SESSIONS]
assert len(days) == SESSIONS

# All full event records stay under the repository's ignored private audit root.
LOG_ENABLED = "--no-log" not in sys.argv
RUN_ID = stable_id("run", "V5U_LOGGED_V1", POLICY_NAME, ACTION_MODE,
                   days[0], SESSIONS, CONFIG_HASH, MANIFEST_HASH)
RUN_PATH = ROOT / "audit" / "batch4a6_v1" / RUN_ID
if RUN_PATH.exists() and any(RUN_PATH.iterdir()):
    raise FileExistsError("VERSIONED_RUN_ALREADY_EXISTS:" + str(RUN_PATH))
JOURNAL = LocalJournal(
    RUN_PATH, run_id=RUN_ID,
    policy_id=POLICY_NAME, config_hash=CONFIG_HASH, manifest_hash=MANIFEST_HASH
) if LOG_ENABLED else None
RECORDED_PHASES = set()

def snap(phase, decision_day, execution_day, state, marks, nav_value, budget,
         *, cash_value=None, receivable=None, origin="decision_time", orders=None,
         cost=None, **extra):
    if JOURNAL is None:
        return None
    if cash_value is None:
        cash_value = cash
    if receivable is None:
        receivable = float(ledger.outstanding() + provisional_total())
    values = exposure(state, marks, nav_value, cash=cash_value,
                      receivable=receivable, budget=budget,
                      price_source="raw_" + ("Close" if origin == "decision_time" else phase),
                      price_time=decision_day if origin == "decision_time" else execution_day)
    record = JOURNAL.emit("snapshots", decision_date=decision_day,
                        execution_date=execution_day, phase=phase,
                        cutoff=decision_day if origin == "decision_time" else execution_day,
                        origin=origin,
                        decision_id=stable_id("decision", RUN_ID, POLICY_NAME, decision_day),
                        order_ids=orders or [],
                        projected_execution_cost=cost if origin == "decision_time" else None,
                        realized_execution_cost=cost if origin == "execution_time" else None,
                        **values, **extra)
    RECORDED_PHASES.add((execution_day, phase))
    return record

cash = START_CASH
positions = {}
pending = []
trades = []
daily = []
ledger = DividendLedger()
provisional_claims = {}
provisional_events_used = set()
previous_nav = START_CASH
previous_day = None
blocker = None
rejections = []
plans_count = 0
overlay_trim_events = 0
overlay_trim_shares = 0
last_plan = None
last_budget = None

def provisional_total():
    return sum(provisional_claims.values(), Decimal("0"))

def mark(day, field):
    return (
        cash
        + sum(
            p["shares"] * price(t, day, field)
            for t, p in positions.items()
        )
        + float(ledger.outstanding())
        + float(provisional_total())
    )

for day in days:
    try:
        # A payment converts an existing receivable to cash.
        cash += float(ledger.settle(day))

        # Process ex-date actions before the opening auction.
        affected = set(positions)
        affected.update(
            o["ticker"] for o in pending
            if o["action"] == "BUY"
        )

        for ticker in sorted(affected):
            if previous_day is None:
                continue

            f0 = factor(ticker, previous_day)
            f1 = factor(ticker, day)

            action = ACTION_INDEX.get(
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

        open_before = mark(day, "Open")
        overnight_pnl = open_before - previous_nav

        if previous_day is not None:
            snap("S3_PRE_FILL", previous_day, day, positions,
                 {t: price(t, day, "Open") for t in positions},
                 open_before, last_budget, origin="execution_time")

        # A same-opening buy cannot depend on uncertain
        # proceeds from another same-opening sell.
        opening_buy_budget = cash
        opening_buy_spent = 0.0
        cost_today = 0.0

        orders = sorted(
            pending,
            key=lambda o: 0 if o["action"] == "SELL" else 1
        )
        pending = []

        seen_today = set()

        for order in orders:
            ticker = order["ticker"]
            side = order["action"]
            qty = int(order["shares"])

            if (
                order["signal_date"] != previous_day
                or qty <= 0
                or ticker in seen_today
            ):
                raise RuntimeError("INVALID_PENDING_ORDER")

            seen_today.add(ticker)
            opening = price(ticker, day, "Open")
            execution = opening * (
                1 - SLIP if side == "SELL" else 1 + SLIP
            )
            execution_cost = qty * opening * SLIP + FEE

            if side == "SELL":
                p = positions.get(ticker)
                if p is None or qty > p["shares"]:
                    raise RuntimeError("INVALID_SELL_QUANTITY")

                cash += qty * execution - FEE
                p["shares"] -= qty

                if p["shares"] == 0:
                    del positions[ticker]

            elif side == "BUY":
                debit = qty * execution + FEE

                if ticker in positions:
                    raise RuntimeError("UNSUPPORTED_POSITION_TOPUP")

                if (
                    debit + opening_buy_spent
                    > opening_buy_budget + 1e-7
                ):
                    if JOURNAL:
                        JOURNAL.lifecycle(
                            decision_date=previous_day, execution_date=day,
                            decision_id=stable_id("decision", RUN_ID, POLICY_NAME, previous_day),
                            order_id=stable_id("order", RUN_ID, POLICY_NAME, previous_day, ticker, side),
                            state="REJECTED", reason="OPENING_CASH_BUDGET",
                            accepted_planned_shares=qty, filled_shares=0)
                    rejections.append({
                        "date": day,
                        "ticker": ticker,
                        "reason": "OPENING_CASH_BUDGET",
                    })
                    continue

                if (
                    qty * opening / open_before
                    > STRAT.order_entry_position_cap + 1e-9
                ):
                    if JOURNAL:
                        JOURNAL.lifecycle(
                            decision_date=previous_day, execution_date=day,
                            decision_id=stable_id("decision", RUN_ID, POLICY_NAME, previous_day),
                            order_id=stable_id("order", RUN_ID, POLICY_NAME, previous_day, ticker, side),
                            state="REJECTED", reason="OPENING_POSITION_CAP",
                            accepted_planned_shares=qty, filled_shares=0)
                    rejections.append({
                        "date": day,
                        "ticker": ticker,
                        "reason": "OPENING_POSITION_CAP",
                    })
                    continue

                opening_buy_spent += debit
                cash -= debit

                positions[ticker] = {
                    "shares": qty,
                    "initial_shares": qty,
                    "avg_cost": execution,
                    "initial_stop": order["stop"],
                    "entry_date": day,
                    "sector": order["sector"],
                }

                if execution <= order["stop"]:
                    raise RuntimeError(
                        "FILLED_BELOW_STOP_REQUIRES_POLICY:"
                        + ticker
                    )

            else:
                raise RuntimeError("UNKNOWN_ORDER_ACTION")

            cost_today += execution_cost

            trades.append({
                "date": day,
                "signal_date": order["signal_date"],
                "ticker": ticker,
                "action": side,
                "shares": qty,
                "execution_price": execution,
                "execution_cost": execution_cost,
                "reason": order["reason"],
            })
            if JOURNAL:
                oid = stable_id("order", RUN_ID, POLICY_NAME, previous_day, ticker, side)
                JOURNAL.lifecycle(
                    decision_date=previous_day, execution_date=day,
                    decision_id=stable_id("decision", RUN_ID, POLICY_NAME, previous_day),
                    order_id=oid, state="FILLED", filled_shares=qty,
                    accepted_planned_shares=qty, execution_price=execution,
                    realized_cost=execution_cost)

        open_after = mark(day, "Open")
        if previous_day is not None:
            post = snap("S4_POST_FILL", previous_day, day, positions,
                        {t: price(t, day, "Open") for t in positions},
                        open_after, last_budget, origin="execution_time",
                        cost=cost_today)
            if JOURNAL and last_plan:
                JOURNAL.emit("pairs", decision_date=previous_day,
                             execution_date=day, phase="IMPLEMENTATION_GAP",
                             cutoff=day, origin="execution_time",
                             decision_id=stable_id("decision", RUN_ID, POLICY_NAME, previous_day),
                             had_orders=bool(orders),
                             had_overlay_intervention=any("risk_budget_overlay" in o["reason"] for o in orders),
                             own_overlay_requirement=POLICY_NAME in ("B", "C"),
                             policy_a_reference_only=POLICY_NAME == "A",
                             **implementation_gap(last_plan, post))

        assert math.isclose(
            open_before - open_after,
            cost_today,
            abs_tol=0.0001,
        ), "OPEN_EXECUTION_NAV_IDENTITY_FAILED"

        intraday_pnl = sum(
            p["shares"] * (
                price(t, day) - price(t, day, "Open")
            )
            for t, p in positions.items()
        )

        nav = mark(day, "Close")

        assert math.isclose(
            nav,
            previous_nav + overnight_pnl
            + intraday_pnl - cost_today,
            abs_tol=0.0001,
        ), "DAILY_NAV_IDENTITY_FAILED"

        assert cash >= -0.0001
        assert len(positions) <= STRAT.target_positions

        daily.append({
            "date": day,
            "nav": nav,
            "cash": cash,
            "receivable": float(ledger.outstanding() + provisional_total()),
            "holdings": len(positions),
            "overnight_pnl": overnight_pnl,
            "intraday_pnl": intraday_pnl,
            "execution_cost": cost_today,
        })

        # Risk budget for this day's close; historical trailing data only.
        current_risk_budget = budget_fraction(
            POLICY_NAME,
            sigma_20=(
                float(VOL20.loc[pd.Timestamp(day)])
                if POLICY_NAME == "C" else None
            ),
            sigma_reference=SIGMA_REFERENCE,
        )
        daily[-1]["risk_budget_fraction"] = current_risk_budget
        if JOURNAL and previous_day is not None:
            snap("S5_CLOSE", previous_day, day, positions,
                 {t: price(t, day) for t in positions}, nav,
                 current_risk_budget,
                 origin="execution_time")

        # At the close, plan future orders using only
        # information available through this date.
        if day != days[-1]:
            next_day = days[days.index(day) + 1]
            if JOURNAL:
                snap("S0_PRE_DECISION", day, next_day, positions,
                     {t: price(t, day) for t in positions}, nav,
                     current_risk_budget)
            sectors = defaultdict(float)
            used_risk = 0.0

            for ticker, p in positions.items():
                close = price(ticker, day)
                sectors[p["sector"]] += p["shares"] * close
                used_risk += p["shares"] * (
                    max(0.0, close - p["initial_stop"])
                    + CFG.gap_buffer * close
                )

            # Exit orders are planned but do not release
            # capital or position slots until actually filled.
            for ticker, p in sorted(positions.items()):
                f = features(ticker, day)

                if not f:
                    raise RuntimeError(
                        "MISSING_HOLDING_FEATURES:" + ticker
                    )

                result = plan_mpb_exit(
                    shares=int(p["shares"]),
                    original_shares=int(p["initial_shares"]),
                    entry_cost=float(p["avg_cost"]),
                    initial_stop=float(p["initial_stop"]),
                    close_raw=price(ticker, day),
                    ema21_adjusted=float(f["ema21"]),
                    close_adjusted=float(f["close"]),
                    nav=nav,
                    same_day=(p["entry_date"] == day),
                    policy=POLICY,
                )

                if result.sell_shares > 0:
                    pending.append({
                        "action": "SELL",
                        "signal_date": day,
                        "ticker": ticker,
                        "shares": result.sell_shares,
                        "reason": result.reason,
                    })

            mpb_components = {o["ticker"]: int(o["shares"]) for o in pending}

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
                            1_000_000_000
                            - 0
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

            if JOURNAL:
                s1_state = projected_positions(positions, pending)
                snap("S1_AFTER_MPB_AND_OVERLAY", day, next_day, s1_state,
                     {t: price(t, day) for t in s1_state}, nav,
                     current_risk_budget,
                     orders=[stable_id("order", RUN_ID, POLICY_NAME, day,
                                       o["ticker"], o["action"]) for o in pending])

            projected_cash = cash
            projected_risk = used_risk
            projected_sector = dict(sectors)
            planned_buys = 0
            buy_proposals = {}

            for s in by_day.get(day, []):
                ticker = s["ticker"]
                sector = s["sector"]

                if ticker in positions:
                    continue
                if len(positions) + planned_buys >= STRAT.target_positions:
                    break
                if len(trades) + len(pending) >= (
                    1_000_000_000
                    - 0
                ):
                    break
                if sector in ("", "Unknown", "nan"):
                    continue

                close = price(ticker, day)
                stop = (
                    float(s["planned_stop_adjusted"])
                    * close / price(ticker, day, kind="adjusted")
                )

                if not 0 < stop < close:
                    continue

                per_share = (
                    close - stop
                    + close * (CFG.gap_buffer + SLIP)
                )

                budget = min(
                    CFG.risk_per_position * nav,
                    max(
                        0.0,
                        current_risk_budget * nav
                        - projected_risk,
                    ),
                )

                frame = panel(ticker, "raw")
                prior = frame.loc[:pd.Timestamp(day)].iloc[:-1]
                if len(prior) < 20:
                    continue

                average_volume = float(
                    prior.tail(20)["Volume"].mean()
                )

                limits = [
                    math.floor(max(0, budget - 2*FEE) / per_share),
                    math.floor(
                        min(
                            STRAT.position_buffer_cap,
                            STRAT.order_entry_position_cap,
                            CONTEST.max_position_weight
                        ) * nav / (close * (1+CFG.gap_buffer))
                    ),
                    math.floor(
                        max(
                            0.0,
                            STRAT.max_sector_weight * nav
                            - projected_sector.get(sector, 0)
                        ) / close
                    ),
                    math.floor(
                        average_volume * CFG.max_participation
                    ),
                    math.floor(
                        max(
                            0.0,
                            projected_cash
                            - STRAT.cash_operating_target_dollars - FEE
                        ) / (close * (1 + CFG.gap_buffer))
                    ),
                ]

                q = max(0, min(limits))

                if JOURNAL:
                    requested = max(0, min(limits[:-1]))
                    buy_proposals[ticker] = (requested, q, tuple(limits))
                    proposal_id = stable_id("order", RUN_ID, POLICY_NAME, day, ticker, "BUY")
                    did = stable_id("decision", RUN_ID, POLICY_NAME, day)
                    JOURNAL.lifecycle(
                        decision_date=day, execution_date=next_day,
                        decision_id=did, order_id=proposal_id,
                        state="PROPOSED", ticker=ticker, action="BUY",
                        security_id=s.get("security_id"),
                        requested_shares=requested,
                        decision_reference_price=close, decision_stop=stop,
                        adjustment_factor=factor(ticker, day),
                        strategy_component=s["setup"],
                        cash_available=projected_cash,
                        risk_limit_shares=limits[0], position_limit_shares=limits[1],
                        sector_limit_shares=limits[2], volume_limit_shares=limits[3],
                        cash_limit_shares=limits[4])

                if q * close < STRAT.min_rebalance_dollars:
                    if JOURNAL:
                        JOURNAL.lifecycle(
                            decision_date=day, execution_date=next_day,
                            decision_id=did, order_id=proposal_id,
                            state="REJECTED", reason="MIN_REBALANCE_OR_LIMIT",
                            accepted_planned_shares=0, rejected_planned_shares=requested)
                    continue

                pending.append({
                    "action": "BUY",
                    "signal_date": day,
                    "ticker": ticker,
                    "shares": q,
                    "sector": sector,
                    "stop": stop,
                    "reason": s["setup"],
                })

                projected_cash -= (
                    q * close * (1 + CFG.gap_buffer) + FEE
                )
                projected_risk += q * per_share + 2 * FEE
                projected_sector[sector] = (
                    projected_sector.get(sector, 0) + q * close
                )
                planned_buys += 1

                if JOURNAL and requested > q:
                    JOURNAL.emit(
                        "orders", decision_date=day, execution_date=next_day,
                        phase="ORDER_PARTIAL_PLAN_REJECTION", cutoff=day,
                        origin="decision_time", decision_id=did, order_id=proposal_id,
                        order_state="PARTIAL_PLAN_REJECTION",
                        reason="CASH_OR_OTHER_LIMIT", requested_shares=requested,
                        accepted_planned_shares=q, rejected_planned_shares=requested-q)

            plans_count += len(pending)
            if JOURNAL:
                did = stable_id("decision", RUN_ID, POLICY_NAME, day)
                order_ids = []
                estimated_cost = 0.0
                for o in pending:
                    ticker, side, qty = o["ticker"], o["action"], int(o["shares"])
                    oid = stable_id("order", RUN_ID, POLICY_NAME, day, ticker, side)
                    order_ids.append(oid)
                    close = price(ticker, day)
                    estimated_cost += qty * close * SLIP + FEE
                    if side == "SELL":
                        JOURNAL.lifecycle(
                            decision_date=day, execution_date=next_day,
                            decision_id=did, order_id=oid, state="PROPOSED",
                            ticker=ticker, action=side, requested_shares=qty,
                            security_id=positions[ticker].get("security_id"),
                            mpb_exit_quantity=mpb_components.get(ticker, 0),
                            overlay_reduction_quantity=qty-mpb_components.get(ticker, 0),
                            final_netted_quantity=qty,
                            decision_reference_price=close,
                            decision_stop=positions[ticker]["initial_stop"],
                            adjustment_factor=factor(ticker, day),
                            strategy_component=o["reason"])
                    JOURNAL.lifecycle(
                        decision_date=day, execution_date=next_day,
                        decision_id=did, order_id=oid, state="ACCEPTED",
                        ticker=ticker, action=side, accepted_planned_shares=qty,
                        rejected_planned_shares=0 if side == "SELL" else max(
                            0, buy_proposals[ticker][0]-qty),
                        estimated_cost=qty*close*SLIP+FEE,
                        cash_check="PLANNER" if side == "BUY" else "NOT_APPLICABLE",
                        risk_limit_check="PLANNER" if side == "BUY" else "OVERLAY_OR_MPB",
                        final_planned_order_state="ACCEPTED")
                    JOURNAL.lifecycle(
                        decision_date=day, execution_date=next_day,
                        decision_id=did, order_id=oid, state="QUEUED",
                        queued_shares=qty)
                s2_state = projected_positions(positions, pending)
                last_plan = snap(
                    "S2_FINAL_PLAN", day, next_day, s2_state,
                    {t: price(t, day) for t in s2_state}, nav,
                    current_risk_budget, orders=order_ids, cost=estimated_cost,
                    planner_projected_cash=projected_cash,
                    cash_convention="T_CLOSE_ACTUAL; PLANNER_PROJECTED_CASH_SEPARATE",
                    nav_convention="T_CLOSE_ACTUAL")
                last_budget = current_risk_budget

        previous_nav = nav
        previous_day = day

    except (RuntimeError, ValueError, KeyError) as exc:
        blocker = {"date": day, "reason": str(exc)}
        if JOURNAL:
            if previous_day is not None and last_plan is not None:
                for phase in ("S3_PRE_FILL", "S4_POST_FILL"):
                    if (day, phase) not in RECORDED_PHASES:
                        missing = snap(
                            phase, previous_day, day, positions, {}, None,
                            last_budget, origin="execution_time",
                            error_reason=str(exc))
                        if phase == "S4_POST_FILL":
                            JOURNAL.emit(
                                "pairs", decision_date=previous_day,
                                execution_date=day, phase="IMPLEMENTATION_GAP",
                                cutoff=day, origin="execution_time",
                                decision_id=stable_id("decision", RUN_ID, POLICY_NAME, previous_day),
                                had_orders=bool(last_plan["order_ids"]),
                                had_overlay_intervention=False,
                                own_overlay_requirement=POLICY_NAME in ("B", "C"),
                                policy_a_reference_only=POLICY_NAME == "A",
                                **implementation_gap(last_plan, missing))
            for oid, state in list(JOURNAL.states.items()):
                if state not in {"REJECTED", "FILLED", "CANCELLED", "EXPIRED"}:
                    ddate, edate, did = JOURNAL.order_context[oid]
                    JOURNAL.lifecycle(
                        decision_date=ddate, execution_date=edate,
                        decision_id=did, order_id=oid,
                        state="CANCELLED", reason="SIMULATION_ABORT:" + str(exc))
        break

OUT = RUN_PATH
OUT.mkdir(exist_ok=True)
reconciliation = reconcile_directory(OUT) if JOURNAL else None
if JOURNAL:
    (OUT / "reconciliation.json").write_text(
        json.dumps(reconciliation, indent=2) + "\n"
    )

def write_csv(filename, records):
    if not records:
        return
    with (OUT / filename).open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(records[0])
        )
        writer.writeheader()
        writer.writerows(records)

write_csv(f"p3_lifecycle_v5u_{POLICY_NAME}_daily.csv", daily)
write_csv(f"p3_lifecycle_v5u_{POLICY_NAME}_trades.csv", trades)

buys = sum(t["action"] == "BUY" for t in trades)
sells = sum(t["action"] == "SELL" for t in trades)

summary = {
    "schema": "FMA_MPB_LIFECYCLE_V5U",
    "policy": POLICY_NAME,
    "action_mode": ACTION_MODE,
    "transaction_cap_scenario": "NON_BINDING_RESEARCH_1B",
    "provider_only_payment_policy": "UNSETTLED_RECEIVABLE_NO_CASH_CREDIT",
    "sigma_reference": SIGMA_REFERENCE,
    "overlay_trim_events_planned": overlay_trim_events,
    "overlay_trim_shares_planned": overlay_trim_shares,
    "purpose": "HISTORICAL_SOFTWARE_INTEGRATION_NOT_FINAL_BACKTEST",
    "status": "BLOCKED" if blocker else "PASS",
    "sessions_requested": SESSIONS,
    "sessions_completed": len(daily),
    "simulated_buys": buys,
    "simulated_sells": sells,
    "orders_planned": plans_count,
    "holdings_at_end": len(positions),
    "cash_rejections": rejections,
    "dividend_receivable": str(ledger.outstanding() + provisional_total()),
    "provisional_unpaid_receivable": str(provisional_total()),
    "provisional_event_count": len(provisional_events_used),
    "provisional_events": [
        {"ticker": t, "ex_date": d}
        for t, d in sorted(provisional_events_used)
    ],
    "blocker": blocker,
    "decision_execution_reconciliation": reconciliation,
    "reference_feature_dependency": True,
    "limitations": [
        "Frozen original reference generates technical features.",
        "Entry selection is from previously validated signal CSV.",
        "Opening-market fills are hypothetical.",
        "Same-auction sell proceeds cannot finance opening buys.",
        "Non-verified corporate actions are blocked.",
        "Dividend-adjusted stops are a research assumption.",
        "No auxiliary portfolio allocation.",
        "No partial fills, daily intrabar stop execution, or taxes.",
        "Not a formally verified strategy-performance backtest."
    ],
}

(OUT / f"p3_lifecycle_v5u_{POLICY_NAME}_summary.json").write_text(
    json.dumps(summary, indent=2) + "\n"
)

print("=== MPB MULTI-ASSET LIFECYCLE V3 ===")
print(json.dumps(summary, indent=2))
print("Daily:", OUT / f"p3_lifecycle_v5u_{POLICY_NAME}_daily.csv")
print("Trades:", OUT / f"p3_lifecycle_v5u_{POLICY_NAME}_trades.csv")
