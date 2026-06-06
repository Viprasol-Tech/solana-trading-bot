"""Cross-pool arbitrage detection.

When the same token trades in two pools at different prices, you can buy in the
cheaper pool and sell in the dearer one. This finds the direction and estimates
the profit for a given trade size, accounting for each pool's fee and slippage.

Part of Solana Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations

from solana_trading_bot.amm import ConstantProductPool, optimal_arbitrage_size


@dataclass(slots=True, frozen=True)
class ArbOpportunity:
    """A detected arbitrage opportunity."""

    buy_pool: str  # label/name of the pool to buy base in (cheaper)
    sell_pool: str  # label/name of the pool to sell base in (dearer)
    base_bought: float
    quote_spent: float
    quote_returned: float

    @property
    def profit(self) -> float:
        """Net quote profit (can be negative if fees/slippage eat the edge)."""
        return self.quote_returned - self.quote_spent

    @property
    def roi(self) -> float:
        """Return on the quote staked, as a fraction (0.01 == 1%)."""
        if self.quote_spent <= 0:
            return 0.0
        return self.profit / self.quote_spent

    @property
    def profitable(self) -> bool:
        return self.profit > 0


def _label(pool: ConstantProductPool, fallback: str) -> str:
    return pool.name or fallback


def find_arbitrage(
    pool_a: ConstantProductPool,
    pool_b: ConstantProductPool,
    quote_in: float,
) -> ArbOpportunity:
    """Spend ``quote_in`` buying base in the cheaper pool, sell it in the other.

    Returns the opportunity (which may be unprofitable after fees/slippage).
    """
    if quote_in <= 0:
        raise ValueError("quote_in must be positive")
    # Buy base where the spot price (quote per base) is lower.
    if pool_a.spot_price <= pool_b.spot_price:
        buy, sell, buy_label, sell_label = pool_a, pool_b, "A", "B"
    else:
        buy, sell, buy_label, sell_label = pool_b, pool_a, "B", "A"

    base_bought = buy.amount_out(quote_in, base_to_quote=False)
    quote_returned = sell.amount_out(base_bought, base_to_quote=True)
    return ArbOpportunity(
        buy_pool=_label(buy, buy_label),
        sell_pool=_label(sell, sell_label),
        base_bought=base_bought,
        quote_spent=quote_in,
        quote_returned=quote_returned,
    )


def optimal_arbitrage(
    pool_a: ConstantProductPool,
    pool_b: ConstantProductPool,
) -> ArbOpportunity:
    """Best-sized arbitrage between two pools (profit-maximising quote input).

    Uses the closed-form optimal size; the result is unprofitable (size 0) when
    fees outweigh the price gap.
    """
    if pool_a.spot_price <= pool_b.spot_price:
        buy, sell, buy_label, sell_label = pool_a, pool_b, "A", "B"
    else:
        buy, sell, buy_label, sell_label = pool_b, pool_a, "B", "A"

    size = optimal_arbitrage_size(buy, sell)
    if size <= 0:
        return ArbOpportunity(_label(buy, buy_label), _label(sell, sell_label), 0.0, 0.0, 0.0)
    base_bought = buy.amount_out(size, base_to_quote=False)
    quote_returned = sell.amount_out(base_bought, base_to_quote=True)
    return ArbOpportunity(
        buy_pool=_label(buy, buy_label),
        sell_pool=_label(sell, sell_label),
        base_bought=base_bought,
        quote_spent=size,
        quote_returned=quote_returned,
    )


def scan_pools(
    pools: list[ConstantProductPool],
    quote_in: float | None = None,
) -> list[ArbOpportunity]:
    """Scan every ordered pair across N same-pair pools for arbitrage.

    With ``quote_in`` set, each pair is sized at that fixed input; otherwise each
    pair is sized optimally. Returns only profitable opportunities, best first.

    All pools must trade the *same* token pair (e.g. several SOL/USDC pools across
    different DEXs). Pools should carry a ``name`` so results are identifiable.
    """
    if len(pools) < 2:
        raise ValueError("need at least two pools to scan")
    if quote_in is not None and quote_in <= 0:
        raise ValueError("quote_in must be positive when provided")

    seen: set[frozenset[int]] = set()
    found: list[ArbOpportunity] = []
    for i, j in permutations(range(len(pools)), 2):
        key = frozenset((i, j))
        if key in seen:
            continue
        seen.add(key)
        a, b = pools[i], pools[j]
        op = find_arbitrage(a, b, quote_in) if quote_in is not None else optimal_arbitrage(a, b)
        if op.profitable:
            found.append(op)
    found.sort(key=lambda o: o.profit, reverse=True)
    return found
