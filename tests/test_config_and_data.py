from __future__ import annotations

from pathlib import Path

from zweig_supermodel.config import load_project_config
from zweig_supermodel.data import read_csv_series


def test_load_default_config() -> None:
    config = load_project_config("configs/default.toml")

    assert config.fred.prime_series == "MPRIME"
    assert "sp500" in config.market
    assert config.market["rsp"].source == "nasdaq"
    assert config.market["rsp"].symbol == "RSP"
    assert config.metadata.id == "book"
    assert config.models.four_percent.threshold == 0.04
    assert config.models.super_model.buy_threshold == 6


def test_load_scenario_configs() -> None:
    aggressive = load_project_config("configs/aggressive.toml")
    conservative = load_project_config("configs/conservative.toml")

    assert aggressive.metadata.id == "aggressive"
    assert aggressive.models.four_percent.threshold == 0.03
    assert aggressive.models.super_model.buy_threshold == 5
    assert conservative.metadata.id == "conservative"
    assert conservative.models.four_percent.threshold == 0.05
    assert conservative.models.super_model.buy_threshold == 7


def test_read_csv_series(tmp_path: Path) -> None:
    path = tmp_path / "series.csv"
    path.write_text("date,close\n2020-01-01,100\n2020-01-02,101\n", encoding="utf-8")

    series = read_csv_series(path, value_col="close")

    assert series.iloc[-1] == 101
    assert str(series.index[0].date()) == "2020-01-01"
