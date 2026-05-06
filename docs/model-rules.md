# Model Rules

This repo implements the simplified model structure described in Martin Zweig's
*Winning on Wall Street* and later public summaries. The implementation keeps
the raw indicator scores separate from the combined model so each signal can be
audited.

## Prime Rate Indicator

The Prime Rate Indicator has two model-point values:

- buy mode: 2 points
- sell mode: 0 points

The v1 state machine uses Zweig's 8% dividing line:

- A buy signal occurs on an initial prime-rate cut when the preceding peak was
  below 8%.
- If the preceding peak was 8% or higher, the buy signal waits for either the
  second cut or a cumulative 1 percentage point cut from the peak.
- A sell signal occurs on an initial hike when the preceding low was 8% or
  higher.
- If the preceding low was below 8%, the sell signal waits for either the second
  hike or a cumulative 1 percentage point hike from the low.

## Fed Indicator

The Fed Indicator tracks policy tightening and easing events. It is implemented
as two possible components:

- discount-rate component
- reserve-requirement component

Reserve requirements are optional because modern reserve-requirement history is
not always available in clean public time series form. If omitted, the component
contributes zero points.

Component logic:

- A hike clears active positive points and adds one negative point.
- Consecutive hikes stack additional negative points.
- Each negative point expires independently after six months.
- An initial cut clears active negative points and adds two positive points.
- Initial-cut points decay after six and twelve months.
- Further consecutive cuts add one positive point that expires after six months.
- An initial cut means the first cut after a hike, or the first change after at
  least two years with no changes.

The discount and reserve components are summed into Fed indicator points, then
converted to Monetary Model points:

| Indicator points | Rating | Model points |
| --- | --- | ---: |
| +2 or more | Extremely bullish | 4 |
| 0 or +1 | Neutral | 2 |
| -1 or -2 | Moderately bearish | 1 |
| -3 or fewer | Extremely bearish | 0 |

## Installment Debt Indicator

The Installment Debt Indicator uses non-seasonally adjusted consumer installment
debt. In FRED, v1 defaults to `NONREVNS`, the nonrevolving consumer-credit
series, as the closest public proxy.

The calculation is the year-over-year percentage change:

```text
(current_month / same_month_last_year - 1) * 100
```

Signals:

- buy when the year-over-year change has been falling and drops below 9%
- sell when the year-over-year change has been rising and reaches 9% or more

The output is lagged two months by default to approximate the historical
six-week release delay.

## Monetary Model

The Monetary Model is:

```text
prime points + fed model points + installment debt points
```

It ranges from 0 to 8. It enters buy mode at 6 or higher and stays there until
the model falls to 2 or lower.

## Four Percent Model

The Four Percent Model uses weekly closes. It enters buy mode when the input
series rises 4% or more from a recent weekly low and enters sell mode when it
falls 4% or more from a recent weekly high.

The faithful input is the Value Line Composite-style series. The repo also
supports an S&P 500 variant so the signal can be compared against a more
available series.

## Super Model

The Super Model is:

```text
monetary model points + four percent model points
```

It ranges from 0 to 10. It enters buy mode at 6 or higher and stays there until
the model falls to 3 or lower.

The default backtest exposure follows the book's tested rule:

- buy mode: 100% stocks
- sell mode: 100% cash equivalent

The implementation also emits `book_partial_exposure`, matching the book's
example of a more gradual risk profile:

| Super points | Exposure |
| ---: | ---: |
| 0-2 | 0% |
| 3-4 | 33.3% |
| 5-6 | 66.7% |
| 7-10 | 100% |

## Public References

- Swetye and Ziemba, "Using Zweig's monetary and momentum models in the modern era":
  https://www.tandfonline.com/doi/full/10.1080/21649502.2015.1165917
- Investstrat overview:
  https://investstrat.com/zweig1.html
- FRED series metadata for defaults:
  https://fred.stlouisfed.org/series/MPRIME,
  https://fred.stlouisfed.org/series/NONREVNS,
  https://fred.stlouisfed.org/series/DPCREDIT
