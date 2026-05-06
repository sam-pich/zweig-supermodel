from __future__ import annotations

import pandas as pd

from zweig_supermodel.indicators import (
    book_partial_exposure_for_super_points,
    fed_indicator,
    four_percent_model,
    installment_debt_indicator,
    monetary_model,
    prime_rate_indicator,
    super_model,
)


def test_prime_rate_buys_on_first_cut_below_8(monthly_series) -> None:
    rates = monthly_series([7.0, 7.25, 7.5, 7.25])
    result = prime_rate_indicator(rates)

    assert result.iloc[-1]["signal"] == "buy"
    assert result.iloc[-1]["points"] == 2


def test_prime_rate_above_8_requires_second_or_large_cut(monthly_series) -> None:
    rates = monthly_series([8.0, 8.5, 8.25, 8.0])
    result = prime_rate_indicator(rates)

    assert result.iloc[2]["points"] == 0
    assert result.iloc[3]["signal"] == "buy"
    assert result.iloc[3]["points"] == 2


def test_prime_rate_below_8_requires_second_or_large_hike_for_sell(monthly_series) -> None:
    rates = monthly_series([7.0, 7.25, 7.5, 7.25, 7.0, 7.5, 8.0])
    result = prime_rate_indicator(rates)

    assert "buy" in set(result["signal"])
    assert result.iloc[-1]["signal"] == "sell"
    assert result.iloc[-1]["points"] == 0


def test_fed_initial_cut_scores_four_model_points(monthly_series) -> None:
    rates = monthly_series([5.0, 5.5, 5.25])
    result = fed_indicator(rates)

    assert result.iloc[-1]["indicator_points"] == 2
    assert result.iloc[-1]["points"] == 4
    assert result.iloc[-1]["rating"] == "extremely_bullish"


def test_fed_hikes_expire_after_six_months(monthly_series) -> None:
    rates = monthly_series([5.0, 5.25, 5.25, 5.25, 5.25, 5.25, 5.25, 5.25])
    result = fed_indicator(rates)

    assert result.iloc[1]["indicator_points"] == -1
    assert result.iloc[-1]["indicator_points"] == 0
    assert result.iloc[-1]["points"] == 2


def test_fed_consecutive_hikes_stack_and_expire_independently(monthly_series) -> None:
    rates = monthly_series([5.0, 5.25, 5.5, 5.5, 5.5, 5.5, 5.5, 5.5, 5.5])
    result = fed_indicator(rates)

    assert result.iloc[1]["indicator_points"] == -1
    assert result.iloc[2]["indicator_points"] == -2
    assert result.iloc[7]["indicator_points"] == -1
    assert result.iloc[8]["indicator_points"] == 0


def test_installment_debt_lagged_buy_signal() -> None:
    index = pd.date_range("2020-01-31", periods=15, freq="ME")
    values = [
        100,
        100,
        100,
        100,
        100,
        100,
        100,
        100,
        100,
        100,
        100,
        100,
        110,
        108,
        107,
    ]
    debt = pd.Series(values, index=index)
    result = installment_debt_indicator(debt, signal_lag_months=2)

    assert result.loc[pd.Timestamp("2021-04-30"), "signal"] == "buy"
    assert result.loc[pd.Timestamp("2021-04-30"), "points"] == 2
    assert result.loc[pd.Timestamp("2021-04-30"), "data_date"] == pd.Timestamp("2021-02-28")


def test_four_percent_model_signals_buy_and_sell(weekly_series) -> None:
    close = weekly_series([100, 98, 102, 105, 100])
    result = four_percent_model(close)

    assert result.iloc[2]["signal"] == "buy"
    assert result.iloc[-1]["signal"] == "sell"
    assert result.iloc[-1]["points"] == 0


def test_monetary_and_super_model_hysteresis(monthly_series, weekly_series) -> None:
    index = pd.date_range("2020-01-31", periods=4, freq="ME")
    prime = pd.DataFrame({"points": [2, 2, 0, 0]}, index=index)
    fed = pd.DataFrame({"points": [4, 4, 2, 0]}, index=index)
    installment = pd.DataFrame({"points": [0, 2, 2, 0]}, index=index)
    monetary = monetary_model(prime, fed, installment)

    assert monetary.iloc[0]["state"] == "buy"
    assert monetary.iloc[2]["state"] == "buy"
    assert monetary.iloc[3]["state"] == "sell"

    four = four_percent_model(weekly_series([100, 105, 110, 105, 100, 104, 108]))
    super_result = super_model(monetary, four)

    assert "exposure" in super_result
    assert "book_partial_exposure" in super_result
    assert super_result["points"].max() <= 10
    assert set(super_result["exposure"]).issubset({0.0, 1.0})


def test_book_partial_super_model_exposure_mapping() -> None:
    assert book_partial_exposure_for_super_points(2) == 0.0
    assert book_partial_exposure_for_super_points(4) == 1.0 / 3.0
    assert book_partial_exposure_for_super_points(6) == 2.0 / 3.0
    assert book_partial_exposure_for_super_points(7) == 1.0
