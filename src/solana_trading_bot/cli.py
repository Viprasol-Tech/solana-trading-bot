"""CLI for Solana Trading Bot.

Demonstrates an AMM swap (with price impact) and a cross-pool arbitrage check on
simulated pools — no RPC, no wallet, no risk.

Part of Solana Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import typer
from rich.console import Console

from solana_trading_bot import __version__
from solana_trading_bot.amm import ConstantProductPool, min_received
from solana_trading_bot.arbitrage import find_arbitrage

app = typer.Typer(add_completion=False, help="Solana Trading Bot — by Viprasol Tech.")
console = Console()


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(f"solana-trading-bot [bold cyan]{__version__}[/] — by Viprasol Tech")


@app.command()
def swap(amount: float = 10.0, slippage_bps: float = 50.0) -> None:
    """Quote a SOL->USDC swap on a simulated pool with price impact."""
    pool = ConstantProductPool(base=1_000.0, quote=150_000.0)  # ~150 USDC/SOL
    out = pool.amount_out(amount, base_to_quote=True)
    impact = pool.price_impact(amount, base_to_quote=True)
    console.print(f"Swap {amount} SOL -> [bold]{out:,.2f} USDC[/]")
    console.print(f"Price impact:  [bold yellow]{impact * 100:.3f}%[/]")
    console.print(
        f"Min received:  {min_received(out, slippage_bps):,.2f} USDC ({slippage_bps:.0f} bps)"
    )


@app.command()
def arb(quote_in: float = 1_000.0) -> None:
    """Check a cross-pool arbitrage opportunity on two simulated pools."""
    pool_a = ConstantProductPool(base=1_000.0, quote=150_000.0)  # 150 USDC/SOL
    pool_b = ConstantProductPool(base=1_000.0, quote=153_000.0)  # 153 USDC/SOL
    op = find_arbitrage(pool_a, pool_b, quote_in)
    console.print(f"Buy base in pool [bold]{op.buy_pool}[/], sell in the other")
    console.print(f"Spent {op.quote_spent:,.2f} -> returned {op.quote_returned:,.2f} USDC")
    color = "green" if op.profitable else "red"
    console.print(f"Net profit:    [bold {color}]{op.profit:+,.2f} USDC[/]")


if __name__ == "__main__":
    app()
