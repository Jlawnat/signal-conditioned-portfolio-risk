"""As-of Norgate input units for the draft sector-free, later-window variant.

Pure transformations only. No strategy decisions or portfolio simulation.
"""

from __future__ import annotations

import math

REQUIRED = 270
MODES = ("NONE", "CAPITAL", "TOTALRETURN")


class InputBlocked(ValueError):
    pass


def _valid(row, *, volume=True):
    vals = [row.get(k) for k in ("open", "high", "low", "close")]
    if not all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0 for v in vals):
        return False
    op, hi, lo, cl = vals
    if hi < max(op, cl, lo) or lo > min(op, cl, hi):
        return False
    v = row.get("volume")
    return not volume or (isinstance(v, (int, float)) and math.isfinite(v) and v > 0)


def _by_date(rows, cutoff):
    result = {}
    for row in rows:
        day = row["date"]
        if day > cutoff:
            continue
        if day in result:
            raise InputBlocked("DUPLICATE_DATE")
        result[day] = row
    return result


def prepare_pair(stock_views, spy_views, decision_date, *, required=REQUIRED):
    """Return 270 aligned bars normalized to raw decision-date units.

    Inputs contain NONE, CAPITAL and TOTALRETURN rows. Later rows are ignored
    before any validation or factor calculation. A current-vintage uniform
    adjustment cancels through the same-T anchor; vintage PIT is not claimed.
    """
    if required < 21:
        raise ValueError("INVALID_HISTORY_REQUIREMENT")
    result = []
    for views in (stock_views, spy_views):
        if any(mode not in views for mode in MODES):
            raise InputBlocked("MISSING_VIEW")
        maps = {mode: _by_date(views[mode], decision_date) for mode in MODES}
        raw_dates = sorted(maps["NONE"])
        if len(raw_dates) < required or raw_dates[-1] != decision_date:
            raise InputBlocked("INSUFFICIENT_OR_MISSING_T_HISTORY")
        dates = raw_dates[-required:]
        if any(any(day not in maps[mode] for mode in MODES) for day in dates):
            raise InputBlocked("MISSING_ASOF_MODE_ROW")
        anchor_raw = maps["NONE"][decision_date]
        anchor_tr = maps["TOTALRETURN"][decision_date]
        anchor_cap = maps["CAPITAL"][decision_date]
        if not all(_valid(row) for row in (anchor_raw, anchor_tr, anchor_cap)):
            raise InputBlocked("INVALID_ANCHOR_BAR")
        tr_to_raw = anchor_raw["close"] / anchor_tr["close"]
        cap_to_raw = anchor_cap["close"] / anchor_raw["close"]
        normalized, raw_window = [], []
        for day in dates:
            raw, cap, tr = (maps[mode][day] for mode in MODES)
            if not all(_valid(row) for row in (raw, cap, tr)):
                raise InputBlocked("INVALID_OHLCV")
            # Acquired extract empirically has CAPITAL volume in reciprocal
            # CAPITAL price units on every observed row. Fail closed if not.
            capital_price_factor = cap["close"] / raw["close"]
            if not math.isclose(cap["volume"] * capital_price_factor,
                                raw["volume"], rel_tol=1e-5, abs_tol=1e-4):
                raise InputBlocked("CAPITAL_VOLUME_CONVENTION_MISMATCH")
            bar = {"date": day,
                   **{k: tr[k] * tr_to_raw for k in ("open", "high", "low", "close")},
                   "volume": cap["volume"] * cap_to_raw}
            if not _valid(bar):
                raise InputBlocked("INVALID_NORMALIZED_BAR")
            normalized.append(bar)
            raw_window.append(dict(raw))
        result.append({"dates": dates, "signal_bars": normalized,
                       "raw_bars": raw_window, "decision_raw_close": anchor_raw["close"],
                       "tr_to_raw_factor": tr_to_raw,
                       "capital_volume_to_raw_t_factor": cap_to_raw})
    stock, spy = result
    if stock["dates"] != spy["dates"]:
        raise InputBlocked("STOCK_SPY_DATE_MISALIGNMENT")
    return {"decision_date": decision_date, "stock": stock, "spy": spy,
            "price_source_execution": "NONE", "price_source_signal": "TOTALRETURN_NORMALIZED",
            "volume_source_signal": "CAPITAL_NORMALIZED"}


def economic_entry_gate(pair, *, min_buy_price, min_avg_dollar_volume_20):
    """Use raw T close and twenty preceding raw price-volume observations."""
    raw = pair["stock"]["raw_bars"]
    prior = raw[-21:-1]
    if len(prior) != 20:
        raise InputBlocked("MISSING_ECONOMIC_LOOKBACK")
    avg = sum(r["close"] * r["volume"] for r in prior) / 20
    return {"raw_close": raw[-1]["close"], "raw_avg_dollar_volume_20": avg,
            "min_price_pass": raw[-1]["close"] >= min_buy_price,
            "liquidity_pass": avg >= min_avg_dollar_volume_20}


def technical_entry_gate(features):
    """Frozen pure feature predicates excluding its adjusted-unit price/ADV tests."""
    return bool(features and features.get("uptrend")
                and features.get("momentum_63", 0) > 0
                and features.get("momentum_126", 0) > 0
                and features.get("rs_63", 0) > 0
                and features.get("rs_126", 0) > 0
                and features.get("setup") != "watch_only"
                and .015 <= features.get("stop_fraction", -1) <= .10)


def normalized_entry(features, economic):
    return technical_entry_gate(features) and economic["min_price_pass"] and economic["liquidity_pass"]


def decision_stop_raw(features, pair):
    """Feature stop is already in raw T units after same-date normalization."""
    close = features.get("close") if features else None
    stop = features.get("planned_stop_adjusted") if features else None
    raw_close = pair["stock"]["decision_raw_close"]
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (close, stop)):
        raise InputBlocked("MISSING_FEATURE_STOP")
    if not math.isclose(close, raw_close, rel_tol=1e-8) or not 0 < stop < raw_close:
        raise InputBlocked("STOP_NOT_IN_RAW_T_UNITS")
    return stop


def raw_execution_mark(row, expected_date, field="open"):
    """Accept a single NONE row at the required open/close, never an adjusted view."""
    if row.get("date") != expected_date or field not in ("open", "close") or not _valid(row):
        raise InputBlocked("INVALID_RAW_EXECUTION_ROW")
    if row.get("mode") not in (None, "NONE"):
        raise InputBlocked("EXECUTION_REQUIRES_NONE")
    return row[field]
