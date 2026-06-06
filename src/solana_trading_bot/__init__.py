"""Solana Trading Bot - Solana DEX/AMM trading bot by Viprasol Tech."""

from __future__ import annotations

from solana_trading_bot.amm import (
    ConstantProductPool,
    effective_price,
    min_received,
    optimal_arbitrage_size,
)
from solana_trading_bot.arbitrage import (
    ArbOpportunity,
    find_arbitrage,
    optimal_arbitrage,
    scan_pools,
)
from solana_trading_bot.liquidity import (
    LPPosition,
    add_liquidity,
    impermanent_loss,
    position_pnl,
    remove_liquidity,
)
from solana_trading_bot.report import (
    SwapReport,
    build_swap_report,
    depth_curve,
    max_size_for_impact,
)
from solana_trading_bot.routing import Hop, Route, Router

__version__ = "0.2.0"
__author__ = "Viprasol Tech Private Limited"
__all__ = [
    "ArbOpportunity",
    "ConstantProductPool",
    "Hop",
    "LPPosition",
    "Route",
    "Router",
    "SwapReport",
    "__version__",
    "add_liquidity",
    "build_swap_report",
    "depth_curve",
    "effective_price",
    "find_arbitrage",
    "impermanent_loss",
    "max_size_for_impact",
    "min_received",
    "optimal_arbitrage",
    "optimal_arbitrage_size",
    "position_pnl",
    "remove_liquidity",
    "scan_pools",
]
