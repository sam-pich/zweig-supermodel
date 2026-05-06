from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from zweig_supermodel.time import to_monthly_last


@dataclass(frozen=True)
class PerformanceStats:
    start: str
    end: str
    periods: int
    final_equity: float
    total_return: float
    cagr: float
    annualized_volatility: float
    sharpe: float
    max_drawdown: float
    average_exposure: float
    percent_periods_invested: float
    exposure_changes: int
    invested_period_wins: int
    invested_period_losses: int

    def as_dict(self) -> dict[str, float | int | str]:
        return {
            "start": self.start,
            "end": self.end,
            "periods": self.periods,
            "final_equity": self.final_equity,
            "total_return": self.total_return,
            "cagr": self.cagr,
            "annualized_volatility": self.annualized_volatility,
            "sharpe": self.sharpe,
            "max_drawdown": self.max_drawdown,
            "average_exposure": self.average_exposure,
            "percent_periods_invested": self.percent_periods_invested,
            "exposure_changes": self.exposure_changes,
            "invested_period_wins": self.invested_period_wins,
            "invested_period_losses": self.invested_period_losses,
        }


@dataclass(frozen=True)
class BacktestResult:
    monthly: pd.DataFrame
    stats: PerformanceStats
    benchmark_stats: PerformanceStats
    invested_periods: pd.DataFrame


def _annualized_stats(
    equity: pd.Series, returns: pd.Series, exposure: pd.Series
) -> PerformanceStats:
    clean_equity = equity.dropna()
    clean_returns = returns.reindex(clean_equity.index).fillna(0.0)
    clean_exposure = exposure.reindex(clean_equity.index).fillna(0.0)
    if clean_equity.empty:
        raise ValueError("equity series is empty")

    start = clean_equity.index[0]
    end = clean_equity.index[-1]
    years = max((end - start).days / 365.25, 1 / 12)
    final_equity = float(clean_equity.iloc[-1])
    initial_equity = float(clean_equity.iloc[0])
    total_return = final_equity / initial_equity - 1.0 if initial_equity else np.nan
    cagr = (final_equity / initial_equity) ** (1.0 / years) - 1.0 if initial_equity else np.nan
    volatility = float(clean_returns.std(ddof=0) * np.sqrt(12))
    sharpe = float((clean_returns.mean() * 12) / volatility) if volatility else 0.0
    drawdown = clean_equity / clean_equity.cummax() - 1.0
    exposure_changes = int(clean_exposure.ne(clean_exposure.shift()).sum() - 1)
    exposure_changes = max(exposure_changes, 0)

    wins, losses = _invested_period_win_loss(clean_returns, clean_exposure)

    return PerformanceStats(
        start=start.date().isoformat(),
        end=end.date().isoformat(),
        periods=int(len(clean_equity)),
        final_equity=final_equity,
        total_return=float(total_return),
        cagr=float(cagr),
        annualized_volatility=volatility,
        sharpe=sharpe,
        max_drawdown=float(drawdown.min()),
        average_exposure=float(clean_exposure.mean()),
        percent_periods_invested=float((clean_exposure > 0).mean()),
        exposure_changes=exposure_changes,
        invested_period_wins=wins,
        invested_period_losses=losses,
    )


def _invested_period_win_loss(returns: pd.Series, exposure: pd.Series) -> tuple[int, int]:
    periods = invested_period_table(returns, exposure)
    if periods.empty:
        return 0, 0
    wins = int((periods["period_return"] > 0).sum())
    losses = int((periods["period_return"] <= 0).sum())
    return wins, losses


def invested_period_table(returns: pd.Series, exposure: pd.Series) -> pd.DataFrame:
    active = exposure.fillna(0.0) > 0
    active_index = pd.DatetimeIndex(active.index)
    rows: list[dict[str, object]] = []
    start: pd.Timestamp | None = None
    cumulative = 1.0
    months = 0

    for position, date in enumerate(active_index):
        is_active = bool(active.iloc[position])
        if is_active and start is None:
            start = date
            cumulative = 1.0
            months = 0
        if is_active:
            cumulative *= 1.0 + float(returns.iloc[position])
            months += 1
        if start is not None:
            next_active = bool(active.iloc[position + 1]) if position + 1 < len(active) else False
            if not next_active:
                rows.append(
                    {
                        "start": start,
                        "end": date,
                        "months": months,
                        "period_return": cumulative - 1.0,
                    }
                )
                start = None

    if not rows:
        return pd.DataFrame(columns=["start", "end", "months", "period_return"])
    return pd.DataFrame(rows)


def run_exposure_backtest(
    close: pd.Series,
    model: pd.DataFrame,
    *,
    initial_capital: float = 10_000.0,
) -> BacktestResult:
    """Backtest monthly exposure, applying each month-end signal to the next return."""
    monthly_close = to_monthly_last(close, "close")
    exposure = model["exposure"].reindex(monthly_close.index).ffill().fillna(0.0)
    asset_return = monthly_close.pct_change().fillna(0.0)
    applied_exposure = exposure.shift(1).fillna(0.0)
    strategy_return = asset_return * applied_exposure
    benchmark_return = asset_return
    equity = initial_capital * (1.0 + strategy_return).cumprod()
    benchmark_equity = initial_capital * (1.0 + benchmark_return).cumprod()

    monthly = pd.DataFrame(
        {
            "close": monthly_close,
            "asset_return": asset_return,
            "signal_exposure": exposure,
            "applied_exposure": applied_exposure,
            "strategy_return": strategy_return,
            "benchmark_return": benchmark_return,
            "equity": equity,
            "benchmark_equity": benchmark_equity,
        }
    ).dropna()
    monthly.index.name = "date"

    periods = invested_period_table(strategy_return.reindex(monthly.index), applied_exposure)
    return BacktestResult(
        monthly=monthly,
        stats=_annualized_stats(equity, strategy_return, applied_exposure),
        benchmark_stats=_annualized_stats(
            benchmark_equity, benchmark_return, pd.Series(1.0, index=monthly.index)
        ),
        invested_periods=periods,
    )
