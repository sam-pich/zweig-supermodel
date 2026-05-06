from __future__ import annotations

import pandas as pd

from zweig_supermodel.backtest import run_exposure_backtest


def test_backtest_applies_signal_to_next_month(monthly_series) -> None:
    close = monthly_series([100, 110, 121, 100])
    model = pd.DataFrame(
        {"exposure": [0.0, 1.0, 1.0, 0.0]},
        index=pd.date_range("2020-01-31", periods=4, freq="ME"),
    )

    result = run_exposure_backtest(close, model, initial_capital=100.0)

    assert result.monthly.iloc[1]["strategy_return"] == 0.0
    assert round(result.monthly.iloc[2]["strategy_return"], 10) == 0.1
    assert round(result.monthly.iloc[3]["strategy_return"], 10) == round(100 / 121 - 1, 10)
    assert round(result.stats.final_equity, 10) == round(100.0 * 1.1 * (100 / 121), 10)
    assert round(result.benchmark_stats.final_equity, 10) == 100.0


def test_backtest_counts_invested_periods(monthly_series) -> None:
    close = monthly_series([100, 110, 121, 100, 90, 99])
    model = pd.DataFrame(
        {"exposure": [0.0, 1.0, 1.0, 0.0, 1.0, 1.0]},
        index=pd.date_range("2020-01-31", periods=6, freq="ME"),
    )

    result = run_exposure_backtest(close, model, initial_capital=100.0)

    assert len(result.invested_periods) == 2
    assert result.stats.invested_period_wins == 1
    assert result.stats.invested_period_losses == 1
