# Assumptions

- The first implementation prioritizes signal correctness and auditability over
  transaction costs, slippage, taxes, and cash yield.
- Backtests use month-end signals and apply exposure to the following monthly
  return to reduce lookahead bias.
- Current incomplete calendar months are dropped during monthly resampling.
- Installment debt signals are lagged two months to approximate the roughly
  six-week publication delay described in the book.
- Reserve-requirement data is optional and defaults to zero contribution.
- The Four Percent Model supports both Value Line-style input and an S&P 500
  comparison variant. The S&P 500 variant is not treated as the faithful Zweig
  model.
- RSP is used as the initial equal-weighted S&P 500 proxy.
- User-provided book excerpts or validation tables should be added as fixtures
  before finalizing any published performance claims.
