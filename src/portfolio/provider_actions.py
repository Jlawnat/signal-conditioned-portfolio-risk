"""Provider corporate actions for exploratory simulation.

Provider reconciliation is NOT independent verification.
No payment or declaration dates are inferred.
"""

import json
import math
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo


def action_date(key):
    try:
        value = float(key)
        if 1_000_000_000 <= value <= 2_500_000_000:
            return datetime.fromtimestamp(
                value, ZoneInfo("America/New_York")
            ).date().isoformat()
    except (ValueError, TypeError, OverflowError):
        pass

    result = str(key)[:10]
    date.fromisoformat(result)
    return result


def index_actions(manifest_path):
    manifest = json.loads(Path(manifest_path).read_text())
    index = {}

    for filename, panel in manifest["panels"].items():
        if not (
            filename.startswith("adjusted/")
            and filename.endswith(".csv")
        ):
            continue

        ticker = Path(filename).stem
        actions = (
            panel.get("attributes", {})
            .get("corporate_action_events", {})
        )

        for kind, entries in actions.items():
            if not entries:
                continue
            if not isinstance(entries, dict):
                raise ValueError(
                    f"INVALID_ACTION_STRUCTURE:{ticker}:{kind}"
                )

            for timestamp, payload in entries.items():
                day = action_date(timestamp)
                event = index.setdefault(
                    (ticker, day),
                    {"dividends": [], "splits": [], "other": []}
                )

                if kind == "dividends":
                    value = (
                        payload.get("amount")
                        if isinstance(payload, dict)
                        else payload
                    )
                    event["dividends"].append(
                        Decimal(str(value))
                    )
                elif kind == "splits":
                    event["splits"].append(payload)
                else:
                    event["other"].append((kind, payload))

    return index


def checked_dividend_amount(
    action, prior_raw_close, factor_ratio
):
    if (
        action is None
        or action["splits"]
        or action["other"]
        or len(action["dividends"]) != 1
    ):
        raise ValueError("UNSUPPORTED_OR_AMBIGUOUS_ACTION")

    amount = action["dividends"][0]
    previous = Decimal(str(prior_raw_close))

    if not 0 < amount < previous:
        raise ValueError("INVALID_DIVIDEND_AMOUNT")

    if not math.isfinite(factor_ratio):
        raise ValueError("INVALID_ADJUSTMENT_RATIO")

    expected = float(
        Decimal("1") / (Decimal("1") - amount / previous)
    )

    if abs(factor_ratio / expected - 1) > 0.0005:
        raise ValueError("PROVIDER_FACTOR_MISMATCH")

    return amount
