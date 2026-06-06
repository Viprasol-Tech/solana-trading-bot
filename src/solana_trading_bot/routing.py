"""Multi-hop routing across a graph of AMM pools.

A real DEX aggregator (Jupiter, 1inch) routes a trade through several pools to get
the best output — e.g. SOL -> USDC -> BONK when no direct SOL/BONK pool exists, or
when the indirect path simply quotes better. This module models pools as edges in a
token graph and finds the best path (by output) up to a maximum hop count.

Part of Solana Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from solana_trading_bot.amm import ConstantProductPool


@dataclass(slots=True, frozen=True)
class PoolEdge:
    """A directed quote across one pool: ``token_in`` -> ``token_out``."""

    token_in: str
    token_out: str
    pool: ConstantProductPool
    base_to_quote: bool

    def quote(self, amount_in: float) -> float:
        """Output amount for swapping ``amount_in`` of ``token_in`` through the pool."""
        return self.pool.amount_out(amount_in, base_to_quote=self.base_to_quote)


@dataclass(slots=True, frozen=True)
class Hop:
    """One leg of a routed swap."""

    token_in: str
    token_out: str
    pool_name: str
    amount_in: float
    amount_out: float


@dataclass(slots=True, frozen=True)
class Route:
    """A complete multi-hop route with the per-hop breakdown."""

    hops: tuple[Hop, ...]
    amount_in: float
    amount_out: float

    @property
    def path(self) -> tuple[str, ...]:
        """Token symbols along the route, e.g. ``("SOL", "USDC", "BONK")``."""
        if not self.hops:
            return ()
        return (self.hops[0].token_in, *(h.token_out for h in self.hops))

    @property
    def hop_count(self) -> int:
        return len(self.hops)

    @property
    def effective_price(self) -> float:
        """Output per unit input across the whole route."""
        if self.amount_in <= 0:
            return 0.0
        return self.amount_out / self.amount_in


@dataclass(slots=True)
class Router:
    """Routes trades across a set of pools modelled as a token graph.

    Each pool contributes two directed edges (base->quote and quote->base). Tokens
    are identified by symbol; you name each side when you register the pool.
    """

    edges: list[PoolEdge] = field(default_factory=list)

    def add_pool(
        self,
        pool: ConstantProductPool,
        base_token: str,
        quote_token: str,
    ) -> Router:
        """Register a pool, wiring both swap directions into the graph."""
        if base_token == quote_token:
            raise ValueError("a pool needs two distinct tokens")
        self.edges.append(PoolEdge(base_token, quote_token, pool, base_to_quote=True))
        self.edges.append(PoolEdge(quote_token, base_token, pool, base_to_quote=False))
        return self

    def _edges_from(self, token: str) -> list[PoolEdge]:
        return [e for e in self.edges if e.token_in == token]

    def find_routes(
        self,
        token_in: str,
        token_out: str,
        amount_in: float,
        max_hops: int = 3,
    ) -> list[Route]:
        """Enumerate all simple routes (no repeated token) up to ``max_hops``.

        Returns routes sorted by output amount, best first. Empty if unreachable.
        """
        if amount_in <= 0:
            raise ValueError("amount_in must be positive")
        if max_hops < 1:
            raise ValueError("max_hops must be at least 1")

        results: list[Route] = []

        def walk(
            token: str, amount: float, visited: tuple[str, ...], hops: tuple[Hop, ...]
        ) -> None:
            if len(hops) >= max_hops:
                return
            for edge in self._edges_from(token):
                if edge.token_out in visited:
                    continue
                out = edge.quote(amount)
                if out <= 0:
                    continue
                hop = Hop(edge.token_in, edge.token_out, edge.pool.name, amount, out)
                next_hops = (*hops, hop)
                if edge.token_out == token_out:
                    results.append(Route(next_hops, amount_in, out))
                walk(edge.token_out, out, (*visited, edge.token_out), next_hops)

        walk(token_in, amount_in, (token_in,), ())
        results.sort(key=lambda r: r.amount_out, reverse=True)
        return results

    def best_route(
        self,
        token_in: str,
        token_out: str,
        amount_in: float,
        max_hops: int = 3,
    ) -> Route | None:
        """Best route by output amount, or ``None`` if the pair is unreachable."""
        routes = self.find_routes(token_in, token_out, amount_in, max_hops)
        return routes[0] if routes else None
