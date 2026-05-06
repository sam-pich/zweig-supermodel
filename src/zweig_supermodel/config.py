from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class FredConfig(BaseModel):
    cache_dir: str = "data/cache/fred"
    prime_series: str = "MPRIME"
    discount_series: list[str] = Field(default_factory=lambda: ["INTDSRUSM193N", "DPCREDIT"])
    installment_debt_series: str = "NONREVNS"


class MarketSeriesConfig(BaseModel):
    source: Literal["stooq", "csv", "url_csv", "nasdaq"]
    symbol: str | None = None
    path: str | None = None
    url: str | None = None
    asset_class: str = "stocks"
    stooq_api_key: str = ""
    date_col: str = "date"
    value_col: str = "close"
    label: str
    required: bool = True


class BacktestConfig(BaseModel):
    initial_capital: float = 10_000.0
    cadence: Literal["monthly"] = "monthly"
    start: str = "1950-01-01"
    end: str = ""


class ProjectConfig(BaseModel):
    fred: FredConfig = Field(default_factory=FredConfig)
    market: dict[str, MarketSeriesConfig]
    momentum: dict[str, MarketSeriesConfig] = Field(default_factory=dict)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)


def load_project_config(path: str | Path) -> ProjectConfig:
    with Path(path).open("rb") as handle:
        data = tomllib.load(handle)
    return ProjectConfig.model_validate(data)
