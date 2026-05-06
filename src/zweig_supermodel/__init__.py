"""Martin Zweig market timing model research package."""

from zweig_supermodel.backtest import run_exposure_backtest
from zweig_supermodel.indicators import (
    fed_indicator,
    four_percent_model,
    installment_debt_indicator,
    monetary_model,
    prime_rate_indicator,
    super_model,
)

__all__ = [
    "fed_indicator",
    "four_percent_model",
    "installment_debt_indicator",
    "monetary_model",
    "prime_rate_indicator",
    "run_exposure_backtest",
    "super_model",
]
