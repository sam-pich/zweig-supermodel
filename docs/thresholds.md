# Model Thresholds

Thresholds are configured in TOML under `[models.*]`.

```toml
[models.prime_rate]
threshold = 8.0
large_move = 1.0

[models.fed]
stale_months = 6
long_quiet_months = 24

[models.installment_debt]
threshold = 9.0
signal_lag_months = 2

[models.four_percent]
threshold = 0.04

[models.monetary]
buy_threshold = 6
sell_threshold = 2

[models.super]
buy_threshold = 6
sell_threshold = 3
```

Available scenario configs:

- `configs/default.toml`: book-rule baseline.
- `configs/aggressive.toml`: earlier entries and looser tape confirmation.
- `configs/conservative.toml`: later entries and faster risk reduction.

Run one scenario:

```bash
uv run zweig --config configs/default.toml --output artifacts/book
```

Run a dashboard comparison:

```bash
uv run zweig \
  --config configs/default.toml \
  --compare-config configs/aggressive.toml \
  --compare-config configs/conservative.toml \
  --output artifacts/latest
```
