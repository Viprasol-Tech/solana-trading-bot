"""Tests for AMM swap math and cross-pool arbitrage."""

from __future__ import annotations

import math

import pytest

from solana_trading_bot.amm import ConstantProductPool, min_received
from solana_trading_bot.arbitrage import find_arbitrage


def test_pool_rejects_bad_reserves() -> None:
    with pytest.raises(ValueError):
        ConstantProductPool(base=0, quote=100)


def test_spot_price() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    assert math.isclose(pool.spot_price, 150.0)


def test_amount_out_less_than_spot_due_to_impact() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000, fee_bps=0)
    out = pool.amount_out(100, base_to_quote=True)
    # Executed price must be below spot (price impact moves against the taker).
    assert out / 100 < pool.spot_price
    assert out > 0


def test_constant_product_invariant_holds_after_swap() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000, fee_bps=0)
    k_before = pool.base * pool.quote
    pool.apply_swap(50, base_to_quote=True)
    k_after = pool.base * pool.quote
    # With zero fee, k is preserved (within float tolerance).
    assert math.isclose(k_before, k_after, rel_tol=1e-9)


def test_min_received_applies_slippage() -> None:
    assert math.isclose(min_received(1_000, 50), 995.0)


def test_arbitrage_detects_direction() -> None:
    cheap = ConstantProductPool(base=1_000, quote=150_000)  # 150
    dear = ConstantProductPool(base=1_000, quote=153_000)  # 153
    op = find_arbitrage(cheap, dear, quote_in=1_000)
    assert op.buy_pool == "A"  # buy in the cheaper pool
    assert op.base_bought > 0


def test_arbitrage_no_edge_when_pools_equal() -> None:
    a = ConstantProductPool(base=1_000, quote=150_000)
    b = ConstantProductPool(base=1_000, quote=150_000)
    op = find_arbitrage(a, b, quote_in=1_000)
    assert not op.profitable  # fees + slippage make equal-price arb a loss
