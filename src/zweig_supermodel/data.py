from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

from zweig_supermodel.time import as_series

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
STOOQ_DAILY_URL = "https://stooq.com/q/d/l/"
NASDAQ_HISTORICAL_URL = "https://api.nasdaq.com/api/quote/{symbol}/historical"


def read_csv_series(
    path: str | Path,
    *,
    date_col: str = "date",
    value_col: str = "value",
) -> pd.Series:
    frame = pd.read_csv(path)
    if date_col not in frame.columns:
        raise ValueError(f"{path} is missing date column {date_col!r}")
    if value_col not in frame.columns:
        raise ValueError(f"{path} is missing value column {value_col!r}")
    frame[date_col] = pd.to_datetime(frame[date_col])
    series = frame.set_index(date_col)[value_col]
    series.name = value_col
    return as_series(series)


def _download_csv(url: str, params: dict[str, str], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    destination.write_bytes(response.content)


def fetch_fred_series(
    series_id: str,
    *,
    cache_dir: str | Path = "data/cache/fred",
    refresh: bool = False,
) -> pd.Series:
    cache_path = Path(cache_dir) / f"{series_id}.csv"
    if refresh or not cache_path.exists():
        _download_csv(FRED_CSV_URL, {"id": series_id}, cache_path)
    frame = pd.read_csv(cache_path)
    if "observation_date" not in frame.columns or series_id not in frame.columns:
        raise ValueError(f"Unexpected FRED CSV shape for {series_id}")
    frame["observation_date"] = pd.to_datetime(frame["observation_date"])
    values = pd.to_numeric(frame[series_id].replace(".", pd.NA), errors="coerce")
    series = pd.Series(values.to_numpy(), index=frame["observation_date"], name=series_id)
    return as_series(series)


def fetch_fred_series_many(
    series_ids: list[str],
    *,
    cache_dir: str | Path = "data/cache/fred",
    refresh: bool = False,
) -> pd.Series:
    if not series_ids:
        raise ValueError("series_ids cannot be empty")
    series = [
        fetch_fred_series(series_id, cache_dir=cache_dir, refresh=refresh).rename(series_id)
        for series_id in series_ids
    ]
    frame = pd.concat(series, axis=1).sort_index()
    combined = frame.bfill(axis=1).iloc[:, 0].dropna()
    combined.name = "_".join(series_ids)
    return combined


def fetch_stooq_daily(
    symbol: str,
    *,
    cache_dir: str | Path = "data/cache/stooq",
    api_key: str = "",
    refresh: bool = False,
) -> pd.Series:
    safe_symbol = symbol.replace("^", "caret_").replace(".", "_")
    cache_path = Path(cache_dir) / f"{safe_symbol}.csv"
    if refresh or not cache_path.exists():
        params = {"s": symbol, "i": "d"}
        if api_key:
            params["apikey"] = api_key
        _download_csv(STOOQ_DAILY_URL, params, cache_path)
    raw = cache_path.read_text(encoding="utf-8", errors="replace")
    if raw.startswith("Get your apikey"):
        raise ValueError(
            f"Stooq requires an API key for {symbol}. Set stooq_api_key or use a CSV source."
        )
    frame = pd.read_csv(cache_path)
    columns = {column.lower(): column for column in frame.columns}
    date_col = columns.get("date")
    close_col = columns.get("close")
    if date_col is None or close_col is None:
        raise ValueError(f"Unexpected Stooq CSV shape for {symbol}")
    frame[date_col] = pd.to_datetime(frame[date_col])
    series = pd.Series(frame[close_col].to_numpy(), index=frame[date_col], name=symbol)
    return as_series(series)


def fetch_url_csv_series(
    url: str,
    *,
    cache_dir: str | Path = "data/cache/url_csv",
    cache_name: str,
    date_col: str,
    value_col: str,
    refresh: bool = False,
) -> pd.Series:
    cache_path = Path(cache_dir) / cache_name
    if refresh or not cache_path.exists():
        _download_csv(url, {}, cache_path)
    return read_csv_series(cache_path, date_col=date_col, value_col=value_col)


def fetch_nasdaq_daily(
    symbol: str,
    *,
    asset_class: str = "stocks",
    cache_dir: str | Path = "data/cache/nasdaq",
    start: str = "",
    end: str = "",
    refresh: bool = False,
) -> pd.Series:
    cache_path = Path(cache_dir) / f"{symbol.lower()}_{asset_class}.csv"
    if refresh or not cache_path.exists():
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        params = {
            "assetclass": asset_class,
            "fromdate": start or "1900-01-01",
            "todate": end or pd.Timestamp.today().date().isoformat(),
            "limit": "9999",
        }
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        response = requests.get(
            NASDAQ_HISTORICAL_URL.format(symbol=symbol),
            params=params,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data", {}).get("tradesTable", {}).get("rows") or []
        if not rows:
            raise ValueError(f"Nasdaq returned no historical rows for {symbol}")
        frame = pd.DataFrame(rows)
        frame.to_csv(cache_path, index=False)

    frame = pd.read_csv(cache_path)
    if "date" not in frame.columns or "close" not in frame.columns:
        raise ValueError(f"Unexpected Nasdaq CSV shape for {symbol}")
    dates = pd.to_datetime(frame["date"], format="%m/%d/%Y")
    close = (
        frame["close"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
    )
    values = pd.to_numeric(close, errors="coerce")
    series = pd.Series(values.to_numpy(), index=dates, name=symbol).sort_index()
    return as_series(series)
