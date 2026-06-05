"""Cross-pool arbitrage detection.

When the same token trades in two pools at different prices, you can buy in the
cheaper pool and sell in the dearer one. This finds the direction and estimates
the profit for a given trade size, accounting for each pool's fee and slippage.

Part of Solana Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dataclasses import dataclass

from solana_trading_bot.amm import ConstantProductPool


@dataclass(slots=True, frozen=True)
class ArbOpportunity:
    """A detected arbitrage opportunity."""

    buy_pool: str  # "A" or "B" — pool to buy base in (cheaper)
    base_bought: float
    quote_spent: float
    quote_returned: float

    @property
    def profit(self) -> float:
        """Net quote profit (can be negative if fees/slippage eat the edge)."""
        return self.quote_returned - self.quote_spent

    @property
    def profitable(self) -> bool:
        return self.profit > 0


def find_arbitrage(
    pool_a: ConstantProductPool,
    pool_b: ConstantProductPool,
    quote_in: float,
) -> ArbOpportunity:
    """Spend ``quote_in`` buying base in the cheaper pool, sell it in the other.

    Returns the opportunity (which may be unprofitable after fees/slippage).
    """
    # Buy base where the spot price (quote per base) is lower.
    if pool_a.spot_price <= pool_b.spot_price:
        buy, sell, label = pool_a, pool_b, "A"
    else:
        buy, sell, label = pool_b, pool_a, "B"

    base_bought = buy.amount_out(quote_in, base_to_quote=False)
    quote_returned = sell.amount_out(base_bought, base_to_quote=True)
    return ArbOpportunity(
        buy_pool=label,
        base_bought=base_bought,
        quote_spent=quote_in,
        quote_returned=quote_returned,
    )
