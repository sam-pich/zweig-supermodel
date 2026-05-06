from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SignalState = Literal["buy", "sell"]


class MetadataConfig(BaseModel):
    id: str = "book"
    name: str = "Book Rules"
    description: str = "Book-derived thresholds and binary Super Model exposure."


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


class PrimeRateRulesConfig(BaseModel):
    threshold: float = 8.0
    large_move: float = 1.0
    initial_state: SignalState = "sell"


class FedRulesConfig(BaseModel):
    stale_months: int = 6
    long_quiet_months: int = 24


class InstallmentDebtRulesConfig(BaseModel):
    threshold: float = 9.0
    signal_lag_months: int = 2
    initial_state: SignalState = "sell"


class FourPercentRulesConfig(BaseModel):
    threshold: float = 0.04
    initial_state: SignalState = "sell"


class MonetaryRulesConfig(BaseModel):
    buy_threshold: int = 6
    sell_threshold: int = 2
    initial_state: SignalState = "sell"


class SuperRulesConfig(BaseModel):
    buy_threshold: int = 6
    sell_threshold: int = 3
    initial_state: SignalState = "sell"


class ModelRulesConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    prime_rate: PrimeRateRulesConfig = Field(default_factory=PrimeRateRulesConfig)
    fed: FedRulesConfig = Field(default_factory=FedRulesConfig)
    installment_debt: InstallmentDebtRulesConfig = Field(default_factory=InstallmentDebtRulesConfig)
    four_percent: FourPercentRulesConfig = Field(default_factory=FourPercentRulesConfig)
    monetary: MonetaryRulesConfig = Field(default_factory=MonetaryRulesConfig)
    super_model: SuperRulesConfig = Field(default_factory=SuperRulesConfig, alias="super")


class ProjectConfig(BaseModel):
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    fred: FredConfig = Field(default_factory=FredConfig)
    market: dict[str, MarketSeriesConfig]
    momentum: dict[str, MarketSeriesConfig] = Field(default_factory=dict)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    models: ModelRulesConfig = Field(default_factory=ModelRulesConfig)


def load_project_config(path: str | Path) -> ProjectConfig:
    with Path(path).open("rb") as handle:
        data = tomllib.load(handle)
    return ProjectConfig.model_validate(data)
