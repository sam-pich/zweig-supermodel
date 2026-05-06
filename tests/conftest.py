from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import pytest


@pytest.fixture
def monthly_series() -> Callable[[list[float], str], pd.Series]:
    def make(values: list[float], start: str = "2020-01-31") -> pd.Series:
        return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="ME"))

    return make


@pytest.fixture
def weekly_series() -> Callable[[list[float], str], pd.Series]:
    def make(values: list[float], start: str = "2020-01-03") -> pd.Series:
        return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="W-FRI"))

    return make
