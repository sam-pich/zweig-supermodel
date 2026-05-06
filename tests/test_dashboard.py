from __future__ import annotations

import pandas as pd

from zweig_supermodel.backtest import run_exposure_backtest
from zweig_supermodel.dashboard import build_dashboard_payload


def test_dashboard_payload_contains_run_series_and_components(monthly_series) -> None:
    close = monthly_series([100, 110, 105, 115])
    model = pd.DataFrame(
        {
            "monetary_points": [2, 4, 6, 6],
            "four_percent_points": [0, 2, 2, 0],
            "points": [2, 6, 8, 6],
            "state": ["sell", "buy", "buy", "buy"],
            "signal": ["", "buy", "", ""],
            "exposure": [0.0, 1.0, 1.0, 1.0],
            "book_partial_exposure": [0.0, 2.0 / 3.0, 1.0, 2.0 / 3.0],
        },
        index=pd.date_range("2020-01-31", periods=4, freq="ME"),
    )
    result = run_exposure_backtest(close, model)

    payload = build_dashboard_payload({"super_sp500": model}, {"sp500__super_sp500": result})

    assert payload["title"] == "Zweig Super Model"
    assert payload["runs"][0]["id"] == "sp500__super_sp500"
    assert "drawdown" in payload["runs"][0]["monthly"][0]
    assert payload["runs"][0]["signals"][0]["signal"] == "buy"
    assert "super_sp500" in payload["components"]
