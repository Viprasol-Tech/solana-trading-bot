# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/).

## [0.2.0] - 2025

### Added
- **Multi-hop routing** (`routing.py`): a `Router` models pools as a token graph
  and finds the best path by output (`find_routes` / `best_route`) up to a hop
  cap, with a per-hop breakdown — e.g. `SOL -> USDC -> BONK`.
- **Slippage / price-impact report** (`report.py`): `build_swap_report` returns a
  structured `SwapReport` (executed price, impact in bps, fee, min-received);
  `depth_curve` profiles impact across sizes; `max_size_for_impact` finds the
  largest trade under an impact cap via bisection.
- **N-pool arbitrage scanner** (`arbitrage.py`): `scan_pools` checks every pool
  pair across N same-pair pools and returns profitable opportunities sorted by
  profit; `optimal_arbitrage` / `optimal_arbitrage_size` size each trade with a
  closed-form profit-maximising input.
- **LP / position helpers** (`liquidity.py`): `add_liquidity`, `remove_liquidity`,
  `pool_share`, `position_pnl`, and `impermanent_loss` (HODL-vs-LP analytics).
- **AMM additions** (`amm.py`): `amount_in_for_out` (exact-output inverse), `k`
  invariant, `copy`, `effective_price`, optional pool `name`, and reserve/fee
  validation.
- **CLI subcommands**: `swap`, `depth`, `route`, `scan`, `arb`, `lp`, `version`
  (rich tables; `no_args_is_help`).
- Sample simulated pools (`pools.py`), a runnable `examples/quickstart.py`, a
  `py.typed` marker, and a substantially expanded test suite (7 -> 54 tests).

### Changed
- `ArbOpportunity` now carries `sell_pool` and an `roi` property; `find_arbitrage`
  validates its trade size and labels pools by name.
- Flagship README rewrite: features, architecture diagram, API table, roadmap, FAQ.

## [0.1.0] - 2025

### Added
- Initial release of solana-trading-bot: Solana DEX trading bot: AMM swap math, slippage control, cross-pool arbitrage.
