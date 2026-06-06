"""End-to-end example: swap report, routing, arbitrage scan, and LP analytics.

Run it with::

    PYTHONPATH=src python examples/quickstart.py

Everything is on simulated pools - no RPC, wallet, or risk.

Part of Solana Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from solana_trading_bot.amm import ConstantProductPool
from solana_trading_bot.arbitrage import scan_pools
from solana_trading_bot.liquidity import add_liquidity, position_pnl
from solana_trading_bot.pools import sample_router, sample_sol_usdc_pools
from solana_trading_bot.report import build_swap_report, max_size_for_impact


def main() -> None:
    # 1) Quote a swap with a full slippage / price-impact report.
    pool = ConstantProductPool(base=1_000.0, quote=150_000.0, fee_bps=30.0, name="raydium")
    rep = build_swap_report(pool, amount_in=25.0, base_to_quote=True, slippage_bps=50.0)
    print("Swap report:")
    print(f"  25 SOL -> {rep.amount_out:,.2f} USDC")
    print(f"  price impact: {rep.price_impact_bps:.1f} bps")
    print(f"  min received: {rep.min_received:,.2f} USDC")

    # 2) Largest trade that keeps price impact under 1%.
    cap = max_size_for_impact(pool, max_impact=0.01, base_to_quote=True)
    print(f"\nMax size under 1% impact: {cap:,.2f} SOL")

    # 3) Best multi-hop route SOL -> BONK across a small pool graph.
    route = sample_router().best_route("SOL", "BONK", amount_in=5.0, max_hops=3)
    assert route is not None
    print(f"\nBest route: {' -> '.join(route.path)} -> {route.amount_out:,.0f} BONK")

    # 4) Scan several SOL/USDC pools for optimally-sized arbitrage.
    print("\nArbitrage scan:")
    for op in scan_pools(sample_sol_usdc_pools()):
        print(
            f"  buy {op.buy_pool} / sell {op.sell_pool}: {op.profit:+,.2f} USDC (ROI {op.roi:.2%})"
        )

    # 5) Model an LP position and its impermanent loss at a 2x move.
    pos = add_liquidity(pool, base_amount=10.0, total_shares=1_000.0)
    pnl = position_pnl(pos, exit_price=300.0)
    print(f"\nLP @2x: IL {pnl['il_fraction']:.2%} ({pnl['il_quote']:+,.2f} USDC vs HODL)")


if __name__ == "__main__":
    main()
