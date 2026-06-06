"""Tests for multi-hop routing across pools."""

from __future__ import annotations

import pytest

from solana_trading_bot.amm import ConstantProductPool
from solana_trading_bot.pools import sample_router
from solana_trading_bot.routing import Router


def test_direct_route_single_hop() -> None:
    router = Router().add_pool(
        ConstantProductPool(base=1_000, quote=150_000, name="SOL/USDC"),
        "SOL",
        "USDC",
    )
    route = router.best_route("SOL", "USDC", 10.0, max_hops=1)
    assert route is not None
    assert route.path == ("SOL", "USDC")
    assert route.hop_count == 1
    assert route.amount_out > 0


def test_multi_hop_route_found() -> None:
    router = sample_router()
    routes = router.find_routes("SOL", "BONK", 5.0, max_hops=3)
    assert routes
    paths = {r.path for r in routes}
    # Both direct and the two-hop SOL->USDC->BONK should appear.
    assert ("SOL", "BONK") in paths
    assert ("SOL", "USDC", "BONK") in paths


def test_routes_sorted_best_first() -> None:
    router = sample_router()
    routes = router.find_routes("SOL", "BONK", 5.0, max_hops=3)
    outs = [r.amount_out for r in routes]
    assert outs == sorted(outs, reverse=True)
    assert router.best_route("SOL", "BONK", 5.0).amount_out == outs[0]


def test_no_repeated_token_in_path() -> None:
    router = sample_router()
    for r in router.find_routes("SOL", "BONK", 5.0, max_hops=3):
        assert len(set(r.path)) == len(r.path)


def test_unreachable_pair_returns_none() -> None:
    router = Router().add_pool(
        ConstantProductPool(base=1_000, quote=150_000, name="SOL/USDC"),
        "SOL",
        "USDC",
    )
    assert router.best_route("SOL", "BONK", 10.0) is None


def test_effective_price_on_route() -> None:
    router = sample_router()
    route = router.best_route("SOL", "USDC", 10.0, max_hops=1)
    assert route is not None
    assert route.effective_price == route.amount_out / route.amount_in


def test_add_pool_rejects_same_token() -> None:
    with pytest.raises(ValueError):
        Router().add_pool(ConstantProductPool(base=1, quote=1), "SOL", "SOL")


def test_find_routes_rejects_bad_args() -> None:
    router = sample_router()
    with pytest.raises(ValueError):
        router.find_routes("SOL", "BONK", 0.0)
    with pytest.raises(ValueError):
        router.find_routes("SOL", "BONK", 5.0, max_hops=0)
