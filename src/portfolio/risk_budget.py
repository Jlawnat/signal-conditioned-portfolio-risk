"""Research risk-budget policies, without trading execution."""

import math


def budget_fraction(
    policy: str,
    *,
    sigma_20: float | None = None,
    sigma_reference: float | None = None,
) -> float:
    if policy in ("A", "B"):
        return 0.04

    if policy != "C":
        raise ValueError("UNKNOWN_POLICY")

    if (
        sigma_20 is None
        or sigma_reference is None
        or not math.isfinite(sigma_20)
        or not math.isfinite(sigma_reference)
        or sigma_20 <= 0
        or sigma_reference <= 0
    ):
        raise ValueError("INVALID_VOLATILITY")

    multiplier = max(
        0.5, min(1.25, sigma_reference / sigma_20)
    )
    return 0.04 * multiplier


def additional_risk_trim(
    positions,
    already_planned_sells,
    *,
    prices,
    nav,
    risk_fraction,
    gap_buffer=0.01,
):
    """Create extra sell quantities from T-close information.

    positions[ticker]: shares, stop
    already_planned_sells[ticker]: existing planned sell shares

    Returns extra SELL shares, not immediate executions.
    """
    if nav <= 0 or risk_fraction <= 0:
        raise ValueError("INVALID_RISK_TARGET")

    contributions = []
    remaining_risk = 0.0

    for ticker, p in positions.items():
        price = float(prices[ticker])
        stop = float(p["stop"])
        shares = int(p["shares"])
        prior_sell = int(
            already_planned_sells.get(ticker, 0)
        )

        if (
            not math.isfinite(price)
            or not math.isfinite(stop)
            or price <= 0
            or stop <= 0
            or shares < 0
            or not 0 <= prior_sell <= shares
        ):
            raise ValueError("INVALID_POSITION")

        remaining = shares - prior_sell
        per_share = (
            max(0.0, price - stop) + gap_buffer * price
        )
        contribution = remaining * per_share
        remaining_risk += contribution

        if remaining:
            contributions.append((
                ticker, remaining, per_share, contribution
            ))

    limit = nav * risk_fraction
    trims = {}

    for ticker, remaining, unit_risk, contribution in sorted(
        contributions, key=lambda x: (-x[3], x[0])
    ):
        excess = remaining_risk - limit
        if excess <= 1e-7:
            break

        quantity = min(
            remaining,
            max(1, math.ceil(excess / unit_risk - 1e-10))
        )

        trims[ticker] = quantity
        remaining_risk -= quantity * unit_risk

    return {
        "extra_sells": trims,
        "projected_risk_dollars": remaining_risk,
        "budget_dollars": limit,
        "budget_fraction": risk_fraction,
        "projected_within_budget": (
            remaining_risk <= limit + 1e-7
        ),
    }
