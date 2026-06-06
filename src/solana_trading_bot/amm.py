"""Constant-product AMM math (the model behind Raydium / Orca pools).

A pool holds reserves of two tokens and enforces the invariant ``x * y = k``.
Swapping in ``dx`` of one token returns ``dy`` of the other such that the product
of the new reserves (after a fee) stays at least ``k``. This module computes swap
outputs, price impact, and the minimum-received amount for a slippage tolerance.

Part of Solana Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(slots=True)
class ConstantProductPool:
    """A two-token constant-product liquidity pool.

    Args:
        base: Reserve of the base token (e.g. SOL).
        quote: Reserve of the quote token (e.g. USDC).
        fee_bps: Swap fee in basis points (30 = 0.30%, the common DEX default).
        name: Optional human label for the pool (used in routing/scan reports).
    """

    base: float
    quote: float
    fee_bps: float = 30.0
    name: str = ""

    def __post_init__(self) -> None:
        if self.base <= 0 or self.quote <= 0:
            raise ValueError("pool reserves must be positive")
        if not 0 <= self.fee_bps < 10_000:
            raise ValueError("fee_bps must be in [0, 10000)")

    @property
    def spot_price(self) -> float:
        """Quote per base, ignoring fees and slippage (the marginal price)."""
        return self.quote / self.base

    @property
    def k(self) -> float:
        """The constant-product invariant ``x * y``."""
        return self.base * self.quote

    def amount_out(self, amount_in: float, base_to_quote: bool = True) -> float:
        """Output amount for swapping ``amount_in`` (constant-product, after fee)."""
        if amount_in <= 0:
            return 0.0
        fee = self.fee_bps / 10_000.0
        in_reserve, out_reserve = (
            (self.base, self.quote) if base_to_quote else (self.quote, self.base)
        )
        amount_in_after_fee = amount_in * (1.0 - fee)
        # dy = (y * dx') / (x + dx')  — preserves x*y=k on the post-fee amount.
        return (out_reserve * amount_in_after_fee) / (in_reserve + amount_in_after_fee)

    def price_impact(self, amount_in: float, base_to_quote: bool = True) -> float:
        """Fractional price impact of a swap vs. the spot price (0..1)."""
        out = self.amount_out(amount_in, base_to_quote)
        if amount_in <= 0 or out <= 0:
            return 0.0
        exec_price = out / amount_in
        spot = self.spot_price if base_to_quote else 1.0 / self.spot_price
        return abs(spot - exec_price) / spot

    def amount_in_for_out(self, amount_out: float, base_to_quote: bool = True) -> float:
        """Input required to receive exactly ``amount_out`` (inverse of ``amount_out``).

        Raises ``ValueError`` if the requested output drains the output reserve.
        """
        if amount_out <= 0:
            return 0.0
        fee = self.fee_bps / 10_000.0
        in_reserve, out_reserve = (
            (self.base, self.quote) if base_to_quote else (self.quote, self.base)
        )
        if amount_out >= out_reserve:
            raise ValueError("requested output exceeds pool reserves")
        # Invert dy = (y * dx') / (x + dx'); then undo the fee on the input.
        amount_in_after_fee = (in_reserve * amount_out) / (out_reserve - amount_out)
        return amount_in_after_fee / (1.0 - fee)

    def apply_swap(self, amount_in: float, base_to_quote: bool = True) -> float:
        """Execute the swap, mutate reserves, and return the output amount."""
        out = self.amount_out(amount_in, base_to_quote)
        if base_to_quote:
            self.base += amount_in
            self.quote -= out
        else:
            self.quote += amount_in
            self.base -= out
        return out

    def copy(self) -> ConstantProductPool:
        """Return an independent copy (so simulations don't mutate the original)."""
        return ConstantProductPool(self.base, self.quote, self.fee_bps, self.name)


def min_received(amount_out: float, slippage_bps: float) -> float:
    """Minimum acceptable output given a slippage tolerance in basis points."""
    if slippage_bps < 0:
        raise ValueError("slippage_bps must be non-negative")
    return amount_out * (1.0 - slippage_bps / 10_000.0)


def effective_price(amount_in: float, amount_out: float) -> float:
    """Average executed price (out per in) for a fill; 0 if either side is empty."""
    if amount_in <= 0 or amount_out <= 0:
        return 0.0
    return amount_out / amount_in


def optimal_arbitrage_size(
    buy: ConstantProductPool,
    sell: ConstantProductPool,
) -> float:
    """Quote input that maximises arbitrage profit buying base in ``buy``, selling in ``sell``.

    Closed-form for the two-hop constant-product round-trip. Returns 0 when there is
    no profitable edge (i.e. the marginal first unit already loses money to fees).
    """
    fb = 1.0 - buy.fee_bps / 10_000.0
    fs = 1.0 - sell.fee_bps / 10_000.0
    # Reserves: buy = quote->base (in=quote Rq_b, out=base Rb_b); sell = base->quote.
    rq_b, rb_b = buy.quote, buy.base
    rb_s, rq_s = sell.base, sell.quote
    # Profit p(x) maximised where dp/dx = 0; derived for the composed CP swaps.
    numerator = math.sqrt(fb * fs * rq_b * rb_b * rb_s * rq_s) - rq_b * rb_s
    denominator = fb * (rb_s + fs * rb_b)
    x = numerator / denominator
    return max(x, 0.0)
