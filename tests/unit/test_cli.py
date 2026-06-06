"""Smoke tests for the CLI subcommands."""

from __future__ import annotations

from typer.testing import CliRunner

from solana_trading_bot import __version__
from solana_trading_bot.cli import app

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_swap_command() -> None:
    result = runner.invoke(app, ["swap", "--amount", "10", "--slippage-bps", "50"])
    assert result.exit_code == 0
    assert "Price impact" in result.stdout
    assert "Min received" in result.stdout


def test_depth_command() -> None:
    result = runner.invoke(app, ["depth", "--steps", "3"])
    assert result.exit_code == 0
    assert "depth curve" in result.stdout.lower()


def test_route_command() -> None:
    result = runner.invoke(app, ["route", "--amount", "5"])
    assert result.exit_code == 0
    assert "BONK" in result.stdout


def test_scan_command() -> None:
    result = runner.invoke(app, ["scan"])
    assert result.exit_code == 0
    assert "rbitrage" in result.stdout  # "Arbitrage"/"arbitrage"


def test_arb_command() -> None:
    result = runner.invoke(app, ["arb"])
    assert result.exit_code == 0
    assert "profit" in result.stdout.lower()


def test_lp_command() -> None:
    result = runner.invoke(app, ["lp", "--base-amount", "10", "--exit-price", "300"])
    assert result.exit_code == 0
    assert "Imperm" in result.stdout


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code != 0 or "Usage" in result.stdout
