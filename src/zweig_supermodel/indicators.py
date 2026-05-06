from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

import numpy as np
import pandas as pd

from zweig_supermodel.time import (
    lag_month_end_frame,
    months_between,
    to_monthly_last,
    to_weekly_last,
)

SignalState = Literal["buy", "sell"]


@dataclass(frozen=True)
class FedEvent:
    points: int
    expires: pd.Timestamp


def _event_is_active(event: FedEvent, date: pd.Timestamp) -> bool:
    return date <= event.expires


def _empty_indicator(index: pd.DatetimeIndex, column: str) -> pd.DataFrame:
    return pd.DataFrame(index=index, data={column: 0})


def prime_rate_indicator(
    prime_rate: pd.Series,
    *,
    threshold: float = 8.0,
    large_move: float = 1.0,
    initial_state: SignalState = "sell",
) -> pd.DataFrame:
    """Score Zweig's Prime Rate Indicator as 2 points in buy mode or 0 in sell mode."""
    rate = to_monthly_last(prime_rate, "prime_rate")
    state: SignalState = initial_state
    peak = float(rate.iloc[0])
    low = float(rate.iloc[0])
    cuts_from_peak = 0
    hikes_from_low = 0
    rows: list[dict[str, object]] = []
    previous = float(rate.iloc[0])

    for _date, value in rate.items():
        current = float(value)
        signal = ""

        if state == "sell":
            if current > peak:
                peak = current
                cuts_from_peak = 0
            if current < previous:
                cuts_from_peak += 1
                if peak < threshold or cuts_from_peak >= 2 or (peak - current) >= large_move:
                    state = "buy"
                    signal = "buy"
                    low = current
                    hikes_from_low = 0
            elif current > previous:
                peak = max(peak, current)
                cuts_from_peak = 0
        else:
            if current < low:
                low = current
                hikes_from_low = 0
            if current > previous:
                hikes_from_low += 1
                if low >= threshold or hikes_from_low >= 2 or (current - low) >= large_move:
                    state = "sell"
                    signal = "sell"
                    peak = current
                    cuts_from_peak = 0
            elif current < previous:
                low = min(low, current)
                hikes_from_low = 0

        rows.append(
            {
                "prime_rate": current,
                "state": state,
                "signal": signal,
                "points": 2 if state == "buy" else 0,
                "reference_extreme": low if state == "buy" else peak,
            }
        )
        previous = current

    out = pd.DataFrame(rows, index=rate.index)
    out.index.name = "date"
    return out


def _fed_component_indicator(
    rate: pd.Series,
    *,
    stale_months: int = 6,
    long_quiet_months: int = 24,
) -> pd.DataFrame:
    monthly = to_monthly_last(rate, "rate")
    rows: list[dict[str, object]] = []
    events: list[FedEvent] = []
    last_change_date: pd.Timestamp | None = None
    last_direction = 0
    previous = float(monthly.iloc[0])

    for raw_date, value in monthly.items():
        date = cast(pd.Timestamp, raw_date)
        current = float(value)
        events = [event for event in events if _event_is_active(event, date)]
        direction = int(np.sign(current - previous))
        action = ""

        if direction > 0:
            events = [FedEvent(-1, date + pd.DateOffset(months=stale_months))]
            last_change_date = date
            last_direction = direction
            action = "hike"
        elif direction < 0:
            quiet_for_long_enough = (
                last_change_date is None
                or months_between(last_change_date, date) >= long_quiet_months
            )
            initial_cut = last_direction > 0 or quiet_for_long_enough
            if initial_cut:
                events = [
                    FedEvent(1, date + pd.DateOffset(months=stale_months)),
                    FedEvent(1, date + pd.DateOffset(months=stale_months * 2)),
                ]
                action = "initial_cut"
            else:
                events = [event for event in events if event.points > 0]
                events.append(FedEvent(1, date + pd.DateOffset(months=stale_months)))
                action = "cut"
            last_change_date = date
            last_direction = direction

        points = sum(event.points for event in events)
        rows.append(
            {
                "rate": current,
                "action": action,
                "indicator_points": points,
                "active_events": len(events),
            }
        )
        previous = current

    out = pd.DataFrame(rows, index=monthly.index)
    out.index.name = "date"
    return out


def fed_model_points(indicator_points: int) -> int:
    if indicator_points >= 2:
        return 4
    if indicator_points >= 0:
        return 2
    if indicator_points >= -2:
        return 1
    return 0


def fed_rating(indicator_points: int) -> str:
    if indicator_points >= 2:
        return "extremely_bullish"
    if indicator_points >= 0:
        return "neutral"
    if indicator_points >= -2:
        return "moderately_bearish"
    return "extremely_bearish"


def fed_indicator(
    discount_rate: pd.Series,
    reserve_requirement: pd.Series | None = None,
    *,
    stale_months: int = 6,
    long_quiet_months: int = 24,
) -> pd.DataFrame:
    """Score the Fed Indicator from discount-rate and optional reserve-requirement changes."""
    discount = _fed_component_indicator(
        discount_rate,
        stale_months=stale_months,
        long_quiet_months=long_quiet_months,
    ).rename(
        columns={
            "rate": "discount_rate",
            "action": "discount_action",
            "indicator_points": "discount_points",
            "active_events": "discount_events",
        }
    )

    if reserve_requirement is None:
        reserve = _empty_indicator(pd.DatetimeIndex(discount.index), "reserve_points")
        reserve["reserve_requirement"] = np.nan
        reserve["reserve_action"] = ""
        reserve["reserve_events"] = 0
    else:
        reserve = _fed_component_indicator(
            reserve_requirement,
            stale_months=stale_months,
            long_quiet_months=long_quiet_months,
        ).rename(
            columns={
                "rate": "reserve_requirement",
                "action": "reserve_action",
                "indicator_points": "reserve_points",
                "active_events": "reserve_events",
            }
        )

    combined = pd.concat([discount, reserve], axis=1).sort_index().ffill()
    combined["indicator_points"] = combined["discount_points"].fillna(0).astype(int) + combined[
        "reserve_points"
    ].fillna(0).astype(int)
    combined["rating"] = combined["indicator_points"].map(fed_rating)
    combined["points"] = combined["indicator_points"].map(fed_model_points)
    combined.index.name = "date"
    return combined


def installment_debt_indicator(
    installment_debt: pd.Series,
    *,
    threshold: float = 9.0,
    signal_lag_months: int = 2,
    initial_state: SignalState = "sell",
) -> pd.DataFrame:
    """Score installment debt using the non-seasonally adjusted YoY 9% trend rule."""
    debt = to_monthly_last(installment_debt, "installment_debt")
    yoy = (debt / debt.shift(12) - 1.0) * 100.0
    state: SignalState = initial_state
    rows: list[dict[str, object]] = []

    for date in debt.index:
        change = yoy.loc[date]
        previous = yoy.shift(1).loc[date]
        signal = ""
        falling = bool(pd.notna(change) and pd.notna(previous) and change < previous)
        rising = bool(pd.notna(change) and pd.notna(previous) and change > previous)

        if pd.notna(change):
            if falling and change < threshold:
                state = "buy"
                signal = "buy"
            elif rising and change >= threshold:
                state = "sell"
                signal = "sell"

        rows.append(
            {
                "installment_debt": float(debt.loc[date]),
                "yoy_change": float(change) if pd.notna(change) else np.nan,
                "falling": falling,
                "rising": rising,
                "state": state,
                "signal": signal,
                "points": 2 if state == "buy" else 0,
            }
        )

    raw = pd.DataFrame(rows, index=debt.index)
    raw.index.name = "date"
    return lag_month_end_frame(raw, signal_lag_months)


def four_percent_model(
    close: pd.Series,
    *,
    threshold: float = 0.04,
    initial_state: SignalState = "sell",
) -> pd.DataFrame:
    """Run the weekly Four Percent Model on a close series."""
    weekly = to_weekly_last(close, "close")
    if weekly.empty:
        raise ValueError("close series must contain at least one observation")

    state: SignalState = initial_state
    low = float(weekly.iloc[0])
    high = float(weekly.iloc[0])
    rows: list[dict[str, object]] = []

    for _date, value in weekly.items():
        current = float(value)
        signal = ""

        if state == "sell":
            low = min(low, current)
            if current >= low * (1.0 + threshold):
                state = "buy"
                signal = "buy"
                high = current
        else:
            high = max(high, current)
            if current <= high * (1.0 - threshold):
                state = "sell"
                signal = "sell"
                low = current

        rows.append(
            {
                "close": current,
                "state": state,
                "signal": signal,
                "points": 2 if state == "buy" else 0,
                "reference_low": low,
                "reference_high": high,
            }
        )

    out = pd.DataFrame(rows, index=weekly.index)
    out.index.name = "date"
    return out


def monthly_four_percent_points(four_percent: pd.DataFrame) -> pd.DataFrame:
    monthly = four_percent.resample("ME").last().ffill()
    monthly.index.name = "date"
    return monthly


def monetary_model(
    prime: pd.DataFrame,
    fed: pd.DataFrame,
    installment: pd.DataFrame,
    *,
    buy_threshold: int = 6,
    sell_threshold: int = 2,
    initial_state: SignalState = "sell",
) -> pd.DataFrame:
    frame = pd.concat(
        [
            prime["points"].rename("prime_points"),
            fed["points"].rename("fed_points"),
            installment["points"].rename("installment_points"),
        ],
        axis=1,
    ).sort_index()
    frame = frame.ffill().dropna()
    frame["points"] = (
        frame["prime_points"].astype(int)
        + frame["fed_points"].astype(int)
        + frame["installment_points"].astype(int)
    )
    state: SignalState = initial_state
    states: list[str] = []
    signals: list[str] = []

    for points in frame["points"]:
        signal = ""
        if points >= buy_threshold and state != "buy":
            state = "buy"
            signal = "buy"
        elif points <= sell_threshold and state != "sell":
            state = "sell"
            signal = "sell"
        states.append(state)
        signals.append(signal)

    frame["state"] = states
    frame["signal"] = signals
    frame.index.name = "date"
    return frame


def exposure_for_super_points(points: int) -> float:
    if points <= 2:
        return 0.0
    if points <= 4:
        return 0.5
    if points == 5:
        return 0.65
    if points <= 7:
        return 0.8
    return 1.0


def super_model(
    monetary: pd.DataFrame,
    four_percent: pd.DataFrame,
    *,
    buy_threshold: int = 6,
    sell_threshold: int = 3,
    initial_state: SignalState = "sell",
) -> pd.DataFrame:
    four_monthly = monthly_four_percent_points(four_percent)
    frame = pd.concat(
        [
            monetary["points"].rename("monetary_points"),
            four_monthly["points"].rename("four_percent_points"),
        ],
        axis=1,
    ).sort_index()
    frame = frame.ffill().dropna()
    frame["points"] = frame["monetary_points"].astype(int) + frame["four_percent_points"].astype(
        int
    )

    state: SignalState = initial_state
    states: list[str] = []
    signals: list[str] = []
    for points in frame["points"]:
        signal = ""
        if points >= buy_threshold and state != "buy":
            state = "buy"
            signal = "buy"
        elif points <= sell_threshold and state != "sell":
            state = "sell"
            signal = "sell"
        states.append(state)
        signals.append(signal)

    frame["state"] = states
    frame["signal"] = signals
    frame["exposure"] = frame["points"].map(lambda value: exposure_for_super_points(int(value)))
    frame.index.name = "date"
    return frame
