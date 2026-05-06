from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from zweig_supermodel.config import load_project_config
from zweig_supermodel.pipeline import build_signal_tables, run_backtests, write_outputs

app = typer.Typer(help="Build and backtest Martin Zweig's Super Model.")
console = Console()


@app.command()
def run(
    config: Annotated[Path, typer.Option(help="Project config TOML.")] = Path(
        "configs/default.toml"
    ),
    output: Annotated[Path, typer.Option(help="Output directory.")] = Path("artifacts/latest"),
    refresh: Annotated[bool, typer.Option(help="Refresh cached external data.")] = False,
) -> None:
    """Fetch data, build signal tables, run backtests, and write site-ready outputs."""
    project = load_project_config(config)
    signal_tables = build_signal_tables(project, refresh=refresh)
    backtests = run_backtests(project, signal_tables, refresh=refresh)
    write_outputs(output, signal_tables, backtests)

    table = Table(title="Backtest Summary")
    table.add_column("Run")
    table.add_column("CAGR", justify="right")
    table.add_column("Max DD", justify="right")
    table.add_column("Final", justify="right")
    table.add_column("Benchmark CAGR", justify="right")

    for name, result in backtests.items():
        table.add_row(
            name,
            f"{result.stats.cagr:.2%}",
            f"{result.stats.max_drawdown:.2%}",
            f"{result.stats.final_equity:,.0f}",
            f"{result.benchmark_stats.cagr:.2%}",
        )

    console.print(table)
    console.print(f"Wrote outputs to {output}")


if __name__ == "__main__":
    app()
