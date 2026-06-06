"""Liquidity-provider (LP) position helpers for constant-product pools.

Adding liquidity mints LP tokens proportional to your share of the pool; removing
burns them. Because the pool rebalances as the price moves, an LP's holdings drift
versus simply holding the two tokens — the classic *impermanent loss*. This module
sizes deposits/withdrawals, tracks pool share, values positions, and computes
impermanent loss for a price move.

Part of Solana Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from solana_trading_bot.amm import ConstantProductPool


@dataclass(slots=True, frozen=True)
class LPPosition:
    """An LP position: token amounts deposited and LP shares held."""

    base: float
    quote: float
    shares: float
    entry_price: float

    def value_in_quote(self, price: float) -> float:
        """Mark-to-market value of the held tokens at ``price`` (quote per base)."""
        return self.base * price + self.quote


def add_liquidity(
    pool: ConstantProductPool,
    base_amount: float,
    total_shares: float,
) -> LPPosition:
    """Deposit ``base_amount`` of base and the matching quote at the current ratio.

    Mints LP shares proportional to the deposit's fraction of the (pre-deposit)
    pool. ``total_shares`` is the pool's existing LP-token supply.
    """
    if base_amount <= 0:
        raise ValueError("base_amount must be positive")
    if total_shares <= 0:
        raise ValueError("total_shares must be positive")
    quote_amount = base_amount * pool.spot_price  # deposit at the current ratio
    minted = total_shares * (base_amount / pool.base)
    return LPPosition(
        base=base_amount,
        quote=quote_amount,
        shares=minted,
        entry_price=pool.spot_price,
    )


def pool_share(position: LPPosition, total_shares: float) -> float:
    """Fraction of the pool the position represents (0..1)."""
    if total_shares <= 0:
        raise ValueError("total_shares must be positive")
    return position.shares / total_shares


def remove_liquidity(
    pool: ConstantProductPool,
    position: LPPosition,
    total_shares: float,
) -> tuple[float, float]:
    """Tokens returned when burning the position's shares at current reserves.

    Returns ``(base_out, quote_out)`` proportional to the position's pool share.
    """
    share = pool_share(position, total_shares)
    return pool.base * share, pool.quote * share


def impermanent_loss(price_ratio: float) -> float:
    """Impermanent loss (fraction, <= 0) for a price move ``price_new / price_entry``.

    For a 2x move the well-known result is about -5.7%; for no move it is 0.
    """
    if price_ratio <= 0:
        raise ValueError("price_ratio must be positive")
    held_to_lp = 2.0 * math.sqrt(price_ratio) / (1.0 + price_ratio)
    return held_to_lp - 1.0


def position_pnl(
    position: LPPosition,
    exit_price: float,
) -> dict[str, float]:
    """Compare LP value to HODL at ``exit_price`` and quantify impermanent loss.

    Returns ``hodl_value``, ``lp_value``, ``il_fraction``, and ``il_quote``.
    """
    if exit_price <= 0:
        raise ValueError("exit_price must be positive")
    ratio = exit_price / position.entry_price
    # HODL: keep the originally deposited tokens.
    hodl_value = position.value_in_quote(exit_price)
    # LP: reserves rebalance to keep constant product; base scales by 1/sqrt(ratio).
    lp_base = position.base / math.sqrt(ratio)
    lp_quote = position.quote * math.sqrt(ratio)
    lp_value = lp_base * exit_price + lp_quote
    return {
        "hodl_value": hodl_value,
        "lp_value": lp_value,
        "il_fraction": impermanent_loss(ratio),
        "il_quote": lp_value - hodl_value,
    }
