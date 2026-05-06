from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from zweig_supermodel.backtest import BacktestResult, run_exposure_backtest
from zweig_supermodel.config import MarketSeriesConfig, ProjectConfig
from zweig_supermodel.data import (
    fetch_fred_series,
    fetch_fred_series_many,
    fetch_nasdaq_daily,
    fetch_stooq_daily,
    fetch_url_csv_series,
    read_csv_series,
)
from zweig_supermodel.indicators import (
    fed_indicator,
    four_percent_model,
    installment_debt_indicator,
    monetary_model,
    prime_rate_indicator,
    super_model,
)


def _clip_series(series: pd.Series, start: str, end: str) -> pd.Series:
    out = series
    if start:
        out = out[out.index >= pd.Timestamp(start)]
    if end:
        out = out[out.index <= pd.Timestamp(end)]
    return out


def _load_market_series(
    config: MarketSeriesConfig,
    *,
    cache_dir: str | Path,
    start: str = "",
    end: str = "",
    refresh: bool = False,
) -> pd.Series | None:
    if config.source == "stooq":
        if not config.symbol:
            raise ValueError(f"{config.label} is missing symbol")
        return fetch_stooq_daily(
            config.symbol,
            cache_dir=Path(cache_dir) / "stooq",
            api_key=config.stooq_api_key,
            refresh=refresh,
        )

    if config.source == "url_csv":
        if not config.url:
            raise ValueError(f"{config.label} is missing url")
        cache_name = f"{config.label.lower().replace(' ', '_')}.csv"
        return fetch_url_csv_series(
            config.url,
            cache_dir=Path(cache_dir) / "url_csv",
            cache_name=cache_name,
            date_col=config.date_col,
            value_col=config.value_col,
            refresh=refresh,
        )

    if config.source == "nasdaq":
        if not config.symbol:
            raise ValueError(f"{config.label} is missing symbol")
        return fetch_nasdaq_daily(
            config.symbol,
            asset_class=config.asset_class,
            cache_dir=Path(cache_dir) / "nasdaq",
            start=start,
            end=end,
            refresh=refresh,
        )

    if not config.path:
        raise ValueError(f"{config.label} is missing path")
    path = Path(config.path)
    if not path.exists():
        if config.required:
            raise FileNotFoundError(path)
        return None
    return read_csv_series(path, date_col=config.date_col, value_col=config.value_col)


def build_signal_tables(
    config: ProjectConfig,
    *,
    refresh: bool = False,
) -> dict[str, pd.DataFrame]:
    prime_series = fetch_fred_series(
        config.fred.prime_series,
        cache_dir=config.fred.cache_dir,
        refresh=refresh,
    )
    discount_series = fetch_fred_series_many(
        config.fred.discount_series,
        cache_dir=config.fred.cache_dir,
        refresh=refresh,
    )
    installment_series = fetch_fred_series(
        config.fred.installment_debt_series,
        cache_dir=config.fred.cache_dir,
        refresh=refresh,
    )

    start = config.backtest.start
    end = config.backtest.end
    prime = prime_rate_indicator(_clip_series(prime_series, start, end))
    fed = fed_indicator(_clip_series(discount_series, start, end))
    installment = installment_debt_indicator(_clip_series(installment_series, start, end))
    monetary = monetary_model(prime, fed, installment)

    tables = {
        "prime": prime,
        "fed": fed,
        "installment_debt": installment,
        "monetary": monetary,
    }

    market_cache = Path(config.fred.cache_dir).parent
    for name, momentum_config in config.momentum.items():
        close = _load_market_series(
            momentum_config,
            cache_dir=market_cache,
            start=start,
            end=end,
            refresh=refresh,
        )
        if close is None:
            continue
        four = four_percent_model(_clip_series(close, start, end))
        tables[f"four_percent_{name}"] = four
        tables[f"super_{name}"] = super_model(monetary, four)

    if "sp500" in config.market:
        sp500 = _load_market_series(
            config.market["sp500"],
            cache_dir=market_cache,
            start=start,
            end=end,
            refresh=refresh,
        )
        if sp500 is not None:
            four_sp500 = four_percent_model(_clip_series(sp500, start, end))
            tables["four_percent_sp500"] = four_sp500
            tables["super_sp500"] = super_model(monetary, four_sp500)

    return tables


def run_backtests(
    config: ProjectConfig,
    signal_tables: dict[str, pd.DataFrame],
    *,
    refresh: bool = False,
) -> dict[str, BacktestResult]:
    results: dict[str, BacktestResult] = {}
    market_cache = Path(config.fred.cache_dir).parent
    start = config.backtest.start
    end = config.backtest.end

    for target_name, target_config in config.market.items():
        close = _load_market_series(
            target_config,
            cache_dir=market_cache,
            start=start,
            end=end,
            refresh=refresh,
        )
        if close is None:
            continue
        clipped = _clip_series(close, start, end)
        for model_name, model in signal_tables.items():
            if not model_name.startswith("super_"):
                continue
            key = f"{target_name}__{model_name}"
            results[key] = run_exposure_backtest(
                clipped,
                model,
                initial_capital=config.backtest.initial_capital,
            )

    return results


def write_outputs(
    output_dir: str | Path,
    signal_tables: dict[str, pd.DataFrame],
    backtests: dict[str, BacktestResult],
) -> None:
    output = Path(output_dir)
    tables_dir = output / "tables"
    backtests_dir = output / "backtests"
    tables_dir.mkdir(parents=True, exist_ok=True)
    backtests_dir.mkdir(parents=True, exist_ok=True)

    for name, table in signal_tables.items():
        table.to_csv(tables_dir / f"{name}.csv", index=True)

    summary: dict[str, dict[str, object]] = {}
    for name, result in backtests.items():
        run_dir = backtests_dir / name
        run_dir.mkdir(parents=True, exist_ok=True)
        result.monthly.to_csv(run_dir / "monthly.csv", index=True)
        result.invested_periods.to_csv(run_dir / "invested_periods.csv", index=False)
        summary[name] = {
            "strategy": result.stats.as_dict(),
            "benchmark": result.benchmark_stats.as_dict(),
        }

    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
