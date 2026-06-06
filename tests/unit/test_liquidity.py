"""Tests for LP/position helpers."""

from __future__ import annotations

import math

import pytest

from solana_trading_bot.amm import ConstantProductPool
from solana_trading_bot.liquidity import (
    add_liquidity,
    impermanent_loss,
    pool_share,
    position_pnl,
    remove_liquidity,
)


def test_add_liquidity_deposits_at_ratio() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    pos = add_liquidity(pool, base_amount=10, total_shares=1_000)
    assert math.isclose(pos.quote, 1_500.0)  # 10 SOL * 150 USDC/SOL
    assert math.isclose(pos.shares, 10.0)  # 1% of pool -> 1% of shares
    assert math.isclose(pos.entry_price, 150.0)


def test_add_liquidity_rejects_bad_input() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    with pytest.raises(ValueError):
        add_liquidity(pool, 0, 1_000)
    with pytest.raises(ValueError):
        add_liquidity(pool, 10, 0)


def test_pool_share() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    pos = add_liquidity(pool, 10, 1_000)
    assert math.isclose(pool_share(pos, 1_000), 0.01)


def test_remove_liquidity_returns_proportional() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    pos = add_liquidity(pool, 10, 1_000)
    base_out, quote_out = remove_liquidity(pool, pos, 1_000)
    assert math.isclose(base_out, 10.0)
    assert math.isclose(quote_out, 1_500.0)


def test_impermanent_loss_zero_when_no_move() -> None:
    assert math.isclose(impermanent_loss(1.0), 0.0, abs_tol=1e-12)


def test_impermanent_loss_2x_is_known_value() -> None:
    # The textbook value for a 2x price move is about -5.72%.
    assert math.isclose(impermanent_loss(2.0), -0.0572, abs_tol=1e-3)


def test_impermanent_loss_symmetric() -> None:
    # IL is symmetric in the ratio vs its reciprocal.
    assert math.isclose(impermanent_loss(4.0), impermanent_loss(0.25), rel_tol=1e-9)


def test_impermanent_loss_rejects_bad_ratio() -> None:
    with pytest.raises(ValueError):
        impermanent_loss(0)


def test_position_pnl_shows_il_on_move() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    pos = add_liquidity(pool, 10, 1_000)
    pnl = position_pnl(pos, exit_price=300.0)  # 2x move
    assert pnl["lp_value"] < pnl["hodl_value"]  # LP underperforms HODL
    assert pnl["il_quote"] < 0
    assert math.isclose(pnl["il_fraction"], impermanent_loss(2.0), rel_tol=1e-6)


def test_position_pnl_rejects_bad_exit() -> None:
    pool = ConstantProductPool(base=1_000, quote=150_000)
    pos = add_liquidity(pool, 10, 1_000)
    with pytest.raises(ValueError):
        position_pnl(pos, 0)
