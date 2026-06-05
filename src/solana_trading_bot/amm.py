"""Constant-product AMM math (the model behind Raydium / Orca pools).

A pool holds reserves of two tokens and enforces the invariant ``x * y = k``.
Swapping in ``dx`` of one token returns ``dy`` of the other such that the product
of the new reserves (after a fee) stays at least ``k``. This module computes swap
outputs, price impact, and the minimum-received amount for a slippage tolerance.

Part of Solana Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConstantProductPool:
    """A two-token constant-product liquidity pool.

    Args:
        base: Reserve of the base token (e.g. SOL).
        quote: Reserve of the quote token (e.g. USDC).
        fee_bps: Swap fee in basis points (30 = 0.30%, the common DEX default).
    """

    base: float
    quote: float
    fee_bps: float = 30.0

    def __post_init__(self) -> None:
        if self.base <= 0 or self.quote <= 0:
            raise ValueError("pool reserves must be positive")

    @property
    def spot_price(self) -> float:
        """Quote per base, ignoring fees and slippage (the marginal price)."""
        return self.quote / self.base

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


def min_received(amount_out: float, slippage_bps: float) -> float:
    """Minimum acceptable output given a slippage tolerance in basis points."""
    return amount_out * (1.0 - slippage_bps / 10_000.0)
