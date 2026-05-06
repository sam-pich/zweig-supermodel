from __future__ import annotations

import pandas as pd


def as_series(values: pd.Series | pd.DataFrame, value_col: str | None = None) -> pd.Series:
    """Return a numeric Series with a DatetimeIndex."""
    if isinstance(values, pd.DataFrame):
        if value_col is None:
            if len(values.columns) != 1:
                raise ValueError("value_col is required when the DataFrame has multiple columns")
            value_col = str(values.columns[0])
        series = values[value_col]
    else:
        series = values

    out = series.copy()
    out.index = pd.to_datetime(out.index)
    out = pd.to_numeric(out, errors="coerce").dropna().sort_index()
    return out


def month_end_index(index: pd.Index) -> pd.DatetimeIndex:
    dates = pd.to_datetime(index)
    return pd.DatetimeIndex(dates.to_period("M").to_timestamp("M"))


def to_monthly_last(values: pd.Series, value_name: str = "value") -> pd.Series:
    series = as_series(values)
    monthly = series.resample("ME").last().dropna()
    today = pd.Timestamp.today().normalize()
    if not monthly.empty and monthly.index[-1] > today:
        monthly = monthly.iloc[:-1]
    monthly.name = value_name
    return monthly


def to_weekly_last(values: pd.Series, value_name: str = "close") -> pd.Series:
    series = as_series(values)
    weekly = series.resample("W-FRI").last().dropna()
    weekly.name = value_name
    return weekly


def lag_month_end_frame(frame: pd.DataFrame, months: int) -> pd.DataFrame:
    if months <= 0:
        return frame
    out = frame.copy()
    out["data_date"] = out.index
    dates = pd.DatetimeIndex(out.index)
    shifted = pd.DatetimeIndex([date + pd.DateOffset(months=months) for date in dates])
    out.index = month_end_index(shifted)
    out.index.name = "date"
    return out


def months_between(start: pd.Timestamp, end: pd.Timestamp) -> int:
    return (end.year - start.year) * 12 + end.month - start.month
