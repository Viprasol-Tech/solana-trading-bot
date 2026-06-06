"""Sample simulated pools for demos, the CLI, and examples.

These are illustrative constant-product pools across a few token pairs and DEXs.
They are NOT live data — they exist so every command and example runs offline with
no RPC, wallet, or risk.

Part of Solana Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from solana_trading_bot.amm import ConstantProductPool
from solana_trading_bot.routing import Router


def sample_sol_usdc_pools() -> list[ConstantProductPool]:
    """Three SOL/USDC pools at slightly different prices (for arb scanning)."""
    return [
        ConstantProductPool(base=1_000.0, quote=150_000.0, fee_bps=30.0, name="raydium"),
        ConstantProductPool(base=1_000.0, quote=153_000.0, fee_bps=25.0, name="orca"),
        ConstantProductPool(base=1_000.0, quote=149_000.0, fee_bps=20.0, name="meteora"),
    ]


def sample_router() -> Router:
    """A small token graph: SOL/USDC, USDC/BONK, and SOL/BONK pools.

    Lets routing find SOL -> USDC -> BONK and compare it to the direct SOL/BONK pool.
    """
    router = Router()
    router.add_pool(
        ConstantProductPool(base=1_000.0, quote=150_000.0, fee_bps=30.0, name="SOL/USDC"),
        base_token="SOL",
        quote_token="USDC",
    )
    router.add_pool(
        ConstantProductPool(base=2_000_000_000.0, quote=50_000.0, fee_bps=30.0, name="BONK/USDC"),
        base_token="BONK",
        quote_token="USDC",
    )
    router.add_pool(
        ConstantProductPool(base=5.0, quote=14_000_000.0, fee_bps=30.0, name="SOL/BONK"),
        base_token="SOL",
        quote_token="BONK",
    )
    return router
