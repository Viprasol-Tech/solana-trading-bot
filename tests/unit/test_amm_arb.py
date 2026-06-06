"""Tests for AMM swap math and cross-pool arbitrage."""

from __future__ import annotations

import math

import pytest

from solana_trading_bot.amm import (
    ConstantProductPool,
    effective_price,
    min_received,
    optimal_arbitrage_size,
)
from solana_trading_bot.arbitrage import (
    find_arbitrage,
    optimal_arbitrage,
    scan_pools,
)


def test_pool_rejects_bad_reserves() -> None:
    with pytest.raises(ValueError):
        ConstantProductPool(base=0, quote=100)


def test_pool_rejects_bad_fee() -> None:
    with pytest.raises(ValueError):
        ConstantProductPool(base=1, quote=1, fee_bps=10_000)


def test_spot_price() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    assert math.isclose(pool.spot_price, 150.0)


def test_k_property() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    assert math.isclose(pool.k, 150_000_000.0)


def test_amount_out_less_than_spot_due_to_impact() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000, fee_bps=0)
    out = pool.amount_out(100, base_to_quote=True)
    assert out / 100 < pool.spot_price
    assert out > 0


def test_amount_out_zero_for_nonpositive() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    assert pool.amount_out(0) == 0.0
    assert pool.amount_out(-5) == 0.0


def test_amount_in_for_out_round_trips() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000, fee_bps=30)
    want_out = pool.amount_out(10, base_to_quote=True)
    need_in = pool.amount_in_for_out(want_out, base_to_quote=True)
    assert math.isclose(need_in, 10.0, rel_tol=1e-6)


def test_amount_in_for_out_rejects_draining() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    with pytest.raises(ValueError):
        pool.amount_in_for_out(200_000, base_to_quote=True)


def test_constant_product_invariant_holds_after_swap() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000, fee_bps=0)
    k_before = pool.k
    pool.apply_swap(50, base_to_quote=True)
    assert math.isclose(k_before, pool.k, rel_tol=1e-9)


def test_fee_increases_k_after_swap() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000, fee_bps=30)
    k_before = pool.k
    pool.apply_swap(50, base_to_quote=True)
    assert pool.k > k_before  # the fee stays in the pool, growing k


def test_copy_is_independent() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000, name="x")
    clone = pool.copy()
    clone.apply_swap(10)
    assert pool.base == 1_000  # original untouched
    assert clone.name == "x"


def test_min_received_applies_slippage() -> None:
    assert math.isclose(min_received(1_000, 50), 995.0)


def test_min_received_rejects_negative() -> None:
    with pytest.raises(ValueError):
        min_received(1_000, -1)


def test_effective_price() -> None:
    assert math.isclose(effective_price(10, 1_500), 150.0)
    assert effective_price(0, 1_500) == 0.0


def test_arbitrage_detects_direction() -> None:
    cheap = ConstantProductPool(base=1_000, quote=150_000, name="cheap")
    dear = ConstantProductPool(base=1_000, quote=153_000, name="dear")
    op = find_arbitrage(cheap, dear, quote_in=1_000)
    assert op.buy_pool == "cheap"
    assert op.sell_pool == "dear"
    assert op.base_bought > 0


def test_arbitrage_rejects_bad_size() -> None:
    a = ConstantProductPool(base=1_000, quote=150_000)
    b = ConstantProductPool(base=1_000, quote=153_000)
    with pytest.raises(ValueError):
        find_arbitrage(a, b, quote_in=0)


def test_arbitrage_no_edge_when_pools_equal() -> None:
    a = ConstantProductPool(base=1_000, quote=150_000)
    b = ConstantProductPool(base=1_000, quote=150_000)
    op = find_arbitrage(a, b, quote_in=1_000)
    assert not op.profitable


def test_optimal_size_zero_when_no_edge() -> None:
    a = ConstantProductPool(base=1_000, quote=150_000)
    b = ConstantProductPool(base=1_000, quote=150_000)
    assert optimal_arbitrage_size(a, b) == 0.0


def test_optimal_arbitrage_beats_arbitrary_size() -> None:
    cheap = ConstantProductPool(base=1_000, quote=145_000, fee_bps=20, name="cheap")
    dear = ConstantProductPool(base=1_000, quote=155_000, fee_bps=20, name="dear")
    best = optimal_arbitrage(cheap, dear)
    assert best.profitable
    # The optimal size should beat both a tiny and a huge fixed size.
    small = find_arbitrage(cheap, dear, 100)
    large = find_arbitrage(cheap, dear, 100_000)
    assert best.profit >= small.profit
    assert best.profit >= large.profit
    assert best.roi > 0


def test_scan_pools_finds_and_sorts() -> None:
    pools = [
        ConstantProductPool(base=1_000, quote=149_000, fee_bps=20, name="meteora"),
        ConstantProductPool(base=1_000, quote=153_000, fee_bps=20, name="orca"),
        ConstantProductPool(base=1_000, quote=150_000, fee_bps=20, name="raydium"),
    ]
    ops = scan_pools(pools)
    assert ops, "expected profitable opportunities"
    assert all(o.profitable for o in ops)
    # Sorted best-first.
    assert ops == sorted(ops, key=lambda o: o.profit, reverse=True)
    # Best pair is the widest spread: buy meteora, sell orca.
    assert ops[0].buy_pool == "meteora"
    assert ops[0].sell_pool == "orca"


def test_scan_pools_requires_two() -> None:
    with pytest.raises(ValueError):
        scan_pools([ConstantProductPool(base=1, quote=1)])
