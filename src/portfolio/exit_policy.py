"""Independent MPB exit planning.

Research decisions only. No actual or simulated execution.
The caller must supply data known at signal-date close.
"""

import json
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExitParameters:
    levels: tuple
    fractions: tuple
    trim_trigger: float
    trim_target: float

    @classmethod
    def from_json(cls, path):
        data = json.loads(Path(path).read_text())
        if data["schema"] != "MPB_EXIT_REFERENCE_V1":
            raise ValueError("INVALID_POLICY_SCHEMA")
        return cls(
            tuple(data["profit_levels_r"]),
            tuple(data["cumulative_profit_fractions"]),
            float(data["position_trim_trigger"]),
            float(data["position_trim_target"])
        )


@dataclass(frozen=True)
class ExitPlan:
    current_shares: int
    target_shares: int
    reason: str
    r_multiple: float | None
    ema21_raw: float | None

    @property
    def sell_shares(self):
        return self.current_shares - self.target_shares


def plan_mpb_exit(
    *,
    shares,
    original_shares,
    entry_cost,
    initial_stop,
    close_raw,
    ema21_adjusted,
    close_adjusted,
    nav,
    same_day,
    policy,
):
    """Reproduce MPB close-based exit/trim priorities.

    Invalid metadata fails closed rather than guessing.
    Orders are to be simulated on a later session.
    """
    if (
        type(shares) is not int
        or type(original_shares) is not int
        or shares <= 0
        or original_shares < shares
    ):
        raise ValueError("INVALID_POSITION_SHARES")

    values = (
        entry_cost, initial_stop, close_raw,
        close_adjusted, nav, ema21_adjusted
    )
    if not all(
        isinstance(x, (int, float)) and math.isfinite(x)
        for x in values
    ):
        raise ValueError("MISSING_OR_INVALID_MARKET_FEATURES")

    if not (
        0 < initial_stop < entry_cost
        and close_raw > 0
        and close_adjusted > 0
        and ema21_adjusted > 0
        and nav > 0
    ):
        raise ValueError("INVALID_FILL_OR_MARKET_METADATA")

    want = shares
    reason = "hold_mpb_position"
    r_multiple = None
    ema21_raw = (
        ema21_adjusted * close_raw / close_adjusted
    )

    # Mirror the source's same-day management exclusion.
    if not same_day:
        if close_raw <= initial_stop:
            want = 0
            reason = "planned_stop_breach"
        elif close_raw < ema21_raw:
            want = 0
            reason = "trend_exit_below_ema21"
        else:
            r_multiple = (
                (close_raw - entry_cost)
                / (entry_cost - initial_stop)
            )

            if r_multiple >= policy.levels[1]:
                want = min(
                    want,
                    math.floor(
                        original_shares * (1-policy.fractions[1])
                    )
                )
                reason = "cumulative_5R_profit_take"

            elif r_multiple >= policy.levels[0]:
                want = min(
                    want,
                    math.floor(
                        original_shares * (1-policy.fractions[0])
                    )
                )
                reason = "cumulative_3R_profit_take"

        if (
            shares * close_raw / nav
            >= policy.trim_trigger
        ):
            guard = math.floor(
                policy.trim_target * nav / close_raw
            )
            if guard < want:
                want = guard
                reason = "concentration_guard_trim"

    assert 0 <= want <= shares

    return ExitPlan(
        current_shares=shares,
        target_shares=want,
        reason=reason,
        r_multiple=r_multiple,
        ema21_raw=ema21_raw,
    )
