"""CLI for Solana Trading Bot.

Subcommands demonstrate AMM swaps with a slippage/price-impact report, multi-hop
routing across pools, an N-pool arbitrage scanner, and LP/position analytics — all
on simulated pools (no RPC, no wallet, no risk).

Part of Solana Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from solana_trading_bot import __version__
from solana_trading_bot.amm import ConstantProductPool
from solana_trading_bot.arbitrage import optimal_arbitrage, scan_pools
from solana_trading_bot.liquidity import add_liquidity, position_pnl
from solana_trading_bot.pools import sample_router, sample_sol_usdc_pools
from solana_trading_bot.report import build_swap_report, depth_curve

app = typer.Typer(
    add_completion=False, help="Solana Trading Bot - by Viprasol Tech.", no_args_is_help=True
)
console = Console()


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(f"solana-trading-bot [bold cyan]{__version__}[/] - by Viprasol Tech")


@app.command()
def swap(amount: float = 10.0, slippage_bps: float = 50.0) -> None:
    """Quote a SOL->USDC swap with a full slippage / price-impact report."""
    pool = ConstantProductPool(base=1_000.0, quote=150_000.0, name="raydium")
    rep = build_swap_report(pool, amount, base_to_quote=True, slippage_bps=slippage_bps)
    console.print(f"Swap [bold]{amount} SOL[/] -> [bold]{rep.amount_out:,.2f} USDC[/]")
    console.print(f"Spot price:    {rep.spot_price:,.2f} USDC/SOL")
    console.print(f"Exec price:    {rep.executed_price:,.2f} USDC/SOL")
    console.print(f"Price impact:  [bold yellow]{rep.price_impact_bps:.1f} bps[/]")
    console.print(f"Fee paid:      {rep.fee_paid:,.4f} SOL")
    console.print(f"Min received:  {rep.min_received:,.2f} USDC ({slippage_bps:.0f} bps)")


@app.command()
def depth(steps: int = 5, step_size: float = 20.0) -> None:
    """Show how price impact grows with trade size (a liquidity-depth curve)."""
    pool = ConstantProductPool(base=1_000.0, quote=150_000.0, name="raydium")
    sizes = [step_size * (i + 1) for i in range(steps)]
    table = Table(title="Price-impact depth curve (SOL -> USDC)")
    table.add_column("Size (SOL)", justify="right")
    table.add_column("Impact (bps)", justify="right")
    for size, impact in depth_curve(pool, sizes, base_to_quote=True):
        table.add_row(f"{size:,.0f}", f"{impact * 10_000:.1f}")
    console.print(table)


@app.command()
def route(amount: float = 5.0, max_hops: int = 3) -> None:
    """Find the best multi-hop route for SOL -> BONK across pools."""
    router = sample_router()
    routes = router.find_routes("SOL", "BONK", amount, max_hops=max_hops)
    if not routes:
        console.print("[red]No route found.[/]")
        raise typer.Exit(code=1)
    best = routes[0]
    console.print(f"Best route: [bold]{' -> '.join(best.path)}[/] ({best.hop_count} hops)")
    console.print(f"In {amount} SOL -> [bold]{best.amount_out:,.0f} BONK[/]")
    table = Table(title="All routes (best first)")
    table.add_column("Path")
    table.add_column("Hops", justify="right")
    table.add_column("BONK out", justify="right")
    for r in routes:
        table.add_row(" -> ".join(r.path), str(r.hop_count), f"{r.amount_out:,.0f}")
    console.print(table)


@app.command()
def scan(quote_in: float = 0.0) -> None:
    """Scan several SOL/USDC pools for arbitrage (optimal-sized by default)."""
    pools = sample_sol_usdc_pools()
    ops = scan_pools(pools, quote_in=quote_in if quote_in > 0 else None)
    if not ops:
        console.print("[yellow]No profitable arbitrage found.[/]")
        return
    table = Table(title="Arbitrage scan (profitable only)")
    table.add_column("Buy in")
    table.add_column("Sell in")
    table.add_column("Quote in", justify="right")
    table.add_column("Profit", justify="right")
    table.add_column("ROI", justify="right")
    for op in ops:
        table.add_row(
            op.buy_pool,
            op.sell_pool,
            f"{op.quote_spent:,.2f}",
            f"{op.profit:+,.2f}",
            f"{op.roi * 100:.2f}%",
        )
    console.print(table)


@app.command()
def arb(quote_in: float = 0.0) -> None:
    """Best-sized arbitrage between two SOL/USDC pools (optimal if no amount given)."""
    pools = sample_sol_usdc_pools()
    op = optimal_arbitrage(pools[2], pools[1])  # cheapest vs dearest
    if quote_in > 0:
        from solana_trading_bot.arbitrage import find_arbitrage

        op = find_arbitrage(pools[2], pools[1], quote_in)
    console.print(f"Buy in [bold]{op.buy_pool}[/], sell in [bold]{op.sell_pool}[/]")
    console.print(f"Spent {op.quote_spent:,.2f} -> returned {op.quote_returned:,.2f} USDC")
    color = "green" if op.profitable else "red"
    console.print(
        f"Net profit:    [bold {color}]{op.profit:+,.2f} USDC[/] (ROI {op.roi * 100:.2f}%)"
    )


@app.command()
def lp(base_amount: float = 10.0, exit_price: float = 200.0) -> None:
    """Model an LP position and its impermanent loss at an exit price."""
    pool = ConstantProductPool(base=1_000.0, quote=150_000.0, name="raydium")
    total_shares = 1_000.0
    pos = add_liquidity(pool, base_amount, total_shares)
    pnl = position_pnl(pos, exit_price)
    console.print(
        f"Deposited {base_amount} SOL + {pos.quote:,.2f} USDC "
        f"({pos.shares:,.2f} LP shares, entry {pos.entry_price:,.2f})"
    )
    console.print(f"At exit price {exit_price:,.2f} USDC/SOL:")
    console.print(f"  HODL value:  {pnl['hodl_value']:,.2f} USDC")
    console.print(f"  LP value:    {pnl['lp_value']:,.2f} USDC")
    color = "red" if pnl["il_quote"] < 0 else "green"
    console.print(
        f"  Imperm. loss: [bold {color}]{pnl['il_fraction'] * 100:.2f}%[/] "
        f"({pnl['il_quote']:+,.2f} USDC)"
    )


if __name__ == "__main__":
    app()
