from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from zweig_supermodel.backtest import BacktestResult


def _clean_value(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        item = value.item()
        if isinstance(item, int | float | str | bool):
            return item
    return value


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    table = frame.copy()
    if table.index.name:
        table = table.reset_index()
    rows: list[dict[str, Any]] = []
    for row in table.to_dict(orient="records"):
        rows.append({str(key): _clean_value(value) for key, value in row.items()})
    return rows


def _signal_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if "signal" not in frame.columns:
        return []
    signals = frame[frame["signal"].fillna("") != ""]
    return _records(signals)


def _monthly_records(result: BacktestResult) -> list[dict[str, Any]]:
    monthly = result.monthly.copy()
    monthly["drawdown"] = monthly["equity"] / monthly["equity"].cummax() - 1.0
    monthly["benchmark_drawdown"] = (
        monthly["benchmark_equity"] / monthly["benchmark_equity"].cummax() - 1.0
    )
    columns = [
        "close",
        "asset_return",
        "strategy_return",
        "benchmark_return",
        "signal_exposure",
        "applied_exposure",
        "equity",
        "benchmark_equity",
        "drawdown",
        "benchmark_drawdown",
    ]
    return _records(monthly[columns])


def _split_run_id(run_id: str) -> tuple[str, str]:
    if "__" not in run_id:
        return run_id, ""
    target, model = run_id.split("__", 1)
    return target, model


def build_dashboard_payload(
    signal_tables: dict[str, pd.DataFrame],
    backtests: dict[str, BacktestResult],
) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    for run_id, result in sorted(backtests.items()):
        target, model = _split_run_id(run_id)
        score_table = signal_tables.get(model)
        runs.append(
            {
                "id": run_id,
                "target": target,
                "model": model,
                "strategy": result.stats.as_dict(),
                "benchmark": result.benchmark_stats.as_dict(),
                "monthly": _monthly_records(result),
                "investedPeriods": _records(result.invested_periods),
                "scoreTimeline": _records(score_table) if score_table is not None else [],
                "signals": _signal_records(score_table) if score_table is not None else [],
            }
        )

    component_names = [
        "prime",
        "fed",
        "installment_debt",
        "monetary",
        *sorted(name for name in signal_tables if name.startswith("four_percent_")),
        *sorted(name for name in signal_tables if name.startswith("super_")),
    ]
    components = {
        name: _records(signal_tables[name]) for name in component_names if name in signal_tables
    }

    return {
        "generatedAt": datetime.now(UTC).isoformat(),
        "title": "Zweig Super Model",
        "runs": runs,
        "components": components,
        "notes": [
            "Default Super Model exposure follows the book's binary buy/sell rule.",
            "The current public-data run uses the S&P 500 Four Percent Model variant unless Value Line data is supplied.",
            "RSP is used as the first equal-weight S&P 500 proxy when public data is available.",
        ],
    }


def write_dashboard_json(
    path: str | Path,
    signal_tables: dict[str, pd.DataFrame],
    backtests: dict[str, BacktestResult],
) -> None:
    import json

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = build_dashboard_payload(signal_tables, backtests)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
