# Static Dashboard

The web dashboard is a Vite React app under `site/`. It has no backend and reads
one generated file:

```text
site/public/data/dashboard.json
```

Generate that file with:

```bash
uv run zweig --config configs/default.toml --output artifacts/latest
```

Generate comparison scenarios with:

```bash
uv run zweig \
  --config configs/default.toml \
  --compare-config configs/aggressive.toml \
  --compare-config configs/conservative.toml \
  --output artifacts/latest
```

The same run also writes `artifacts/latest/dashboard.json` for research outputs.
Both generated JSON files are ignored by git.

## Local Development

```bash
cd site
npm install
npm run dev
```

## Production Build

```bash
cd site
npm ci
npm run build
```

The static files are emitted to `site/dist/`. A hosted build should generate
fresh dashboard data before building or deploying the site.

## Dashboard Structure

- Headline KPIs compare strategy versus benchmark.
- The run selector can compare threshold scenarios and market targets.
- Equity and drawdown charts show strategy behavior through time.
- Model score, exposure, and signal tables make the timing rules auditable.
- Scenario settings show the thresholds used for the selected run.
- Data notes surface current limitations such as Value Line data availability.
