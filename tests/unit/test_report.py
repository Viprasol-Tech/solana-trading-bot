"""Tests for the slippage / price-impact report."""

from __future__ import annotations

import math

import pytest

from solana_trading_bot.amm import ConstantProductPool
from solana_trading_bot.report import (
    build_swap_report,
    depth_curve,
    max_size_for_impact,
)


def test_swap_report_fields() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000, fee_bps=30)
    rep = build_swap_report(pool, 10, base_to_quote=True, slippage_bps=50)
    assert rep.amount_in == 10
    assert rep.amount_out > 0
    assert math.isclose(rep.spot_price, 150.0)
    assert rep.executed_price < rep.spot_price  # impact moves price against taker
    assert rep.price_impact > 0
    assert math.isclose(rep.price_impact_bps, rep.price_impact * 10_000)
    assert rep.min_received < rep.amount_out
    assert math.isclose(rep.fee_paid, 10 * 30 / 10_000)


def test_swap_report_as_dict() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    d = build_swap_report(pool, 10).as_dict()
    assert set(d) >= {"amount_in", "amount_out", "price_impact_bps", "min_received"}
    assert d["amount_in"] == 10


def test_swap_report_rejects_bad_amount() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    with pytest.raises(ValueError):
        build_swap_report(pool, 0)


def test_depth_curve_monotonic() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    curve = depth_curve(pool, [10, 50, 100, 200], base_to_quote=True)
    impacts = [imp for _, imp in curve]
    assert impacts == sorted(impacts)  # impact grows with size
    assert len(curve) == 4


def test_depth_curve_rejects_empty() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    with pytest.raises(ValueError):
        depth_curve(pool, [])


def test_max_size_for_impact_matches_curve() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000, fee_bps=0)
    target = 0.01  # 1%
    size = max_size_for_impact(pool, target, base_to_quote=True)
    assert size > 0
    # At the found size impact is at (or just under) the target...
    assert pool.price_impact(size, base_to_quote=True) <= target + 1e-6
    # ...and a clearly larger trade exceeds it.
    assert pool.price_impact(size * 1.5, base_to_quote=True) > target


def test_max_size_for_impact_rejects_bad_target() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    with pytest.raises(ValueError):
        max_size_for_impact(pool, 1.5)
