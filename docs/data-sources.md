# Data Sources

## Macro Data

The default macro provider is FRED through the public CSV endpoint:

```text
https://fred.stlouisfed.org/graph/fredgraph.csv?id={SERIES_ID}
```

Default series:

| Purpose | FRED series | Notes |
| --- | --- | --- |
| Prime rate | `MPRIME` | Monthly bank prime loan rate |
| Discount rate | `INTDSRUSM193N`, `DPCREDIT` | Historical discount-rate proxy plus modern primary-credit rate |
| Installment debt proxy | `NONREVNS` | Non-seasonally adjusted nonrevolving consumer credit |

`NONREVNS` is a proxy. Zweig described consumer installment debt; the current
FRED naming and availability make nonrevolving consumer credit the closest public
default. A CSV override should be used if a better historical installment-debt
series is supplied.

## Market Data

The no-key default market providers are:

- S&P 500 index: DataHub/Shiller monthly CSV, updated with recent FRED `SP500`
  values.
- Equal-weight proxy: Nasdaq historical endpoint for `RSP`.

RSP starts in 2003, but Nasdaq may limit no-key history returned by its public
endpoint. Use a local CSV or licensed provider for full-history equal-weight
tests.

The Stooq adapter remains available, but Stooq currently requires an API key for
CSV downloads from this environment. Set `stooq_api_key` in a market config when
using that source.

## Value Line Data

The Four Percent Model is intended for a Value Line Composite-style series. This
repo does not ship licensed Value Line data. Put a CSV at `data/value_line.csv`
with columns:

```csv
date,close
1966-01-07,100.0
```

If the CSV is missing, the CLI skips the Value Line variant and still runs the
S&P 500 momentum variant.
