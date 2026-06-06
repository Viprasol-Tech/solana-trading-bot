"""Slippage and price-impact reporting.

Before sending a swap you want to know: how much output you get, the average
executed price, how far that is from the spot price (price impact), and the
minimum you'll accept at a chosen slippage tolerance. This module produces a
structured report for a single swap and a depth curve across multiple sizes so
you can see how impact grows with trade size.

Part of Solana Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dataclasses import dataclass

from solana_trading_bot.amm import ConstantProductPool, effective_price, min_received


@dataclass(slots=True, frozen=True)
class SwapReport:
    """A structured quote for a single swap."""

    amount_in: float
    amount_out: float
    spot_price: float
    executed_price: float
    price_impact: float
    slippage_bps: float
    min_received: float
    fee_paid: float

    @property
    def price_impact_bps(self) -> float:
        return self.price_impact * 10_000.0

    def as_dict(self) -> dict[str, float]:
        """Plain-dict view, handy for JSON output or assertions."""
        return {
            "amount_in": self.amount_in,
            "amount_out": self.amount_out,
            "spot_price": self.spot_price,
            "executed_price": self.executed_price,
            "price_impact": self.price_impact,
            "price_impact_bps": self.price_impact_bps,
            "slippage_bps": self.slippage_bps,
            "min_received": self.min_received,
            "fee_paid": self.fee_paid,
        }


def build_swap_report(
    pool: ConstantProductPool,
    amount_in: float,
    base_to_quote: bool = True,
    slippage_bps: float = 50.0,
) -> SwapReport:
    """Compute a full slippage / price-impact report for one swap."""
    if amount_in <= 0:
        raise ValueError("amount_in must be positive")
    out = pool.amount_out(amount_in, base_to_quote=base_to_quote)
    spot = pool.spot_price if base_to_quote else 1.0 / pool.spot_price
    return SwapReport(
        amount_in=amount_in,
        amount_out=out,
        spot_price=spot,
        executed_price=effective_price(amount_in, out),
        price_impact=pool.price_impact(amount_in, base_to_quote=base_to_quote),
        slippage_bps=slippage_bps,
        min_received=min_received(out, slippage_bps),
        fee_paid=amount_in * pool.fee_bps / 10_000.0,
    )


def depth_curve(
    pool: ConstantProductPool,
    sizes: list[float],
    base_to_quote: bool = True,
) -> list[tuple[float, float]]:
    """Price impact (fraction) at each trade size — a liquidity-depth profile.

    Returns ``[(size, price_impact), ...]`` for every size in ``sizes``.
    """
    if not sizes:
        raise ValueError("sizes must be non-empty")
    return [(s, pool.price_impact(s, base_to_quote=base_to_quote)) for s in sizes]


def max_size_for_impact(
    pool: ConstantProductPool,
    max_impact: float,
    base_to_quote: bool = True,
    tolerance: float = 1e-6,
) -> float:
    """Largest trade size whose price impact stays at or below ``max_impact``.

    Uses bisection on the monotonically-increasing impact curve.
    """
    if not 0 < max_impact < 1:
        raise ValueError("max_impact must be in (0, 1)")
    lo, hi = 0.0, (pool.base if base_to_quote else pool.quote)
    # Grow an upper bound until its impact exceeds the target.
    while pool.price_impact(hi, base_to_quote=base_to_quote) < max_impact:
        hi *= 2.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if pool.price_impact(mid, base_to_quote=base_to_quote) <= max_impact:
            lo = mid
        else:
            hi = mid
        if hi - lo < tolerance:
            break
    return lo
