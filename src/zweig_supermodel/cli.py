from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from zweig_supermodel.backtest import BacktestResult
from zweig_supermodel.config import ProjectConfig, load_project_config
from zweig_supermodel.dashboard import DashboardScenario, write_dashboard_json_for_scenarios
from zweig_supermodel.pipeline import build_signal_tables, run_backtests, write_outputs

app = typer.Typer(help="Build and backtest Martin Zweig's Super Model.")
console = Console()


def _model_settings(project: ProjectConfig) -> dict[str, Any]:
    return project.models.model_dump(mode="json", by_alias=True)


def _scenario_from_run(
    project: ProjectConfig,
    signal_tables: dict[str, pd.DataFrame],
    backtests: dict[str, BacktestResult],
) -> DashboardScenario:
    return DashboardScenario(
        id=project.metadata.id,
        name=project.metadata.name,
        description=project.metadata.description,
        settings=_model_settings(project),
        signal_tables=signal_tables,
        backtests=backtests,
    )


def _combined_summary(scenarios: list[DashboardScenario]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for scenario in scenarios:
        for name, result in scenario.backtests.items():
            summary[f"{scenario.id}__{name}"] = {
                "scenario": {
                    "id": scenario.id,
                    "name": scenario.name,
                    "description": scenario.description,
                },
                "strategy": result.stats.as_dict(),
                "benchmark": result.benchmark_stats.as_dict(),
            }
    return summary


@app.command()
def run(
    config: Annotated[Path, typer.Option(help="Project config TOML.")] = Path(
        "configs/default.toml"
    ),
    output: Annotated[Path, typer.Option(help="Output directory.")] = Path("artifacts/latest"),
    site_data: Annotated[
        Path | None,
        typer.Option(help="Optional dashboard JSON path for the static site."),
    ] = Path("site/public/data/dashboard.json"),
    compare_config: Annotated[
        list[Path] | None,
        typer.Option(
            "--compare-config",
            help="Additional scenario config to run and include in dashboard output.",
        ),
    ] = None,
    refresh: Annotated[bool, typer.Option(help="Refresh cached external data.")] = False,
) -> None:
    """Fetch data, build signal tables, run backtests, and write site-ready outputs."""
    config_paths = [config, *(compare_config or [])]
    scenarios: list[DashboardScenario] = []
    summary_rows: list[tuple[str, str, BacktestResult]] = []

    for config_path in config_paths:
        project = load_project_config(config_path)
        signal_tables = build_signal_tables(project, refresh=refresh)
        backtests = run_backtests(project, signal_tables, refresh=refresh)
        scenario = _scenario_from_run(project, signal_tables, backtests)
        scenarios.append(scenario)

        scenario_output = output if len(config_paths) == 1 else output / "scenarios" / scenario.id
        write_outputs(
            scenario_output,
            signal_tables,
            backtests,
            dashboard_path=site_data if len(config_paths) == 1 else None,
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            scenario_description=scenario.description,
            settings=scenario.settings,
        )

        for name, result in backtests.items():
            summary_rows.append((scenario.name, name, result))

    if len(scenarios) > 1:
        output.mkdir(parents=True, exist_ok=True)
        (output / "summary.json").write_text(
            json.dumps(_combined_summary(scenarios), indent=2),
            encoding="utf-8",
        )
        write_dashboard_json_for_scenarios(output / "dashboard.json", scenarios)
        if site_data is not None:
            write_dashboard_json_for_scenarios(site_data, scenarios)

    table = Table(title="Backtest Summary")
    table.add_column("Scenario")
    table.add_column("Run")
    table.add_column("CAGR", justify="right")
    table.add_column("Max DD", justify="right")
    table.add_column("Final", justify="right")
    table.add_column("Benchmark CAGR", justify="right")

    for scenario_name, name, result in summary_rows:
        table.add_row(
            scenario_name,
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
