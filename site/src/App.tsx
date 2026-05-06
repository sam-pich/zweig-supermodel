import { Activity, BarChart3, CalendarClock, Gauge, ShieldAlert, TrendingUp } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { ExposureStrip, LineChart, ScoreChart } from "./charts";
import type { DashboardPayload, DashboardRun, Stats } from "./data";
import { loadDashboard } from "./data";

function formatPercent(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

function formatMoney(value: number): string {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
    style: "currency",
    currency: "USD",
  }).format(value);
}

function labelRun(run: DashboardRun): string {
  return `${run.target.toUpperCase()} / ${run.model.replace("super_", "Super ")}`;
}

function deltaClass(strategy: number, benchmark: number): "positive" | "negative" {
  return strategy >= benchmark ? "positive" : "negative";
}

function Kpi({
  label,
  value,
  detail,
  icon,
  tone = "neutral",
}: {
  label: string;
  value: string;
  detail: string;
  icon: ReactNode;
  tone?: "neutral" | "positive" | "negative";
}) {
  return (
    <div className={`kpi ${tone}`}>
      <div className="kpi-top">
        <span>{label}</span>
        {icon}
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function SummaryGrid({ run }: { run: DashboardRun }) {
  const strategy = run.strategy;
  const benchmark = run.benchmark;

  return (
    <section className="kpi-grid">
      <Kpi
        label="CAGR"
        value={formatPercent(strategy.cagr)}
        detail={`Benchmark ${formatPercent(benchmark.cagr)}`}
        tone={deltaClass(strategy.cagr, benchmark.cagr)}
        icon={<TrendingUp size={18} />}
      />
      <Kpi
        label="Max Drawdown"
        value={formatPercent(strategy.max_drawdown)}
        detail={`Benchmark ${formatPercent(benchmark.max_drawdown)}`}
        tone={strategy.max_drawdown >= benchmark.max_drawdown ? "positive" : "negative"}
        icon={<ShieldAlert size={18} />}
      />
      <Kpi
        label="Final Equity"
        value={formatMoney(strategy.final_equity)}
        detail={`Benchmark ${formatMoney(benchmark.final_equity)}`}
        tone={deltaClass(strategy.final_equity, benchmark.final_equity)}
        icon={<BarChart3 size={18} />}
      />
      <Kpi
        label="Sharpe"
        value={strategy.sharpe.toFixed(2)}
        detail={`Benchmark ${benchmark.sharpe.toFixed(2)}`}
        tone={deltaClass(strategy.sharpe, benchmark.sharpe)}
        icon={<Gauge size={18} />}
      />
      <Kpi
        label="Time Invested"
        value={formatPercent(strategy.percent_periods_invested)}
        detail={`${strategy.exposure_changes} exposure changes`}
        icon={<Activity size={18} />}
      />
      <Kpi
        label="Period"
        value={`${strategy.start.slice(0, 4)}-${strategy.end.slice(0, 4)}`}
        detail={`${strategy.periods} monthly observations`}
        icon={<CalendarClock size={18} />}
      />
    </section>
  );
}

function SignalsTable({ run }: { run: DashboardRun }) {
  const rows = [...run.signals].reverse().slice(0, 10);
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Latest Signals</h2>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Signal</th>
              <th>Score</th>
              <th>Monetary</th>
              <th>4% Model</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.date}-${row.signal}`}>
                <td>{row.date}</td>
                <td>
                  <span className={`signal ${row.signal === "buy" ? "buy" : "sell"}`}>
                    {row.signal}
                  </span>
                </td>
                <td>{row.points}</td>
                <td>{row.monetary_points}</td>
                <td>{row.four_percent_points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ComponentSnapshot({ run }: { run: DashboardRun }) {
  const latest = run.scoreTimeline.at(-1);
  const previousSignal = run.signals.at(-1);

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Current Model</h2>
      </div>
      <div className="snapshot">
        <div>
          <span>Super Score</span>
          <strong>{latest?.points ?? "-"}</strong>
        </div>
        <div>
          <span>State</span>
          <strong>{latest?.state ?? "-"}</strong>
        </div>
        <div>
          <span>Monetary</span>
          <strong>{latest?.monetary_points ?? "-"}</strong>
        </div>
        <div>
          <span>4% Model</span>
          <strong>{latest?.four_percent_points ?? "-"}</strong>
        </div>
        <div>
          <span>Last Signal</span>
          <strong>{previousSignal ? `${previousSignal.signal} ${previousSignal.date}` : "-"}</strong>
        </div>
      </div>
    </section>
  );
}

function Notes({ data }: { data: DashboardPayload }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Data Notes</h2>
      </div>
      <ul className="notes">
        {data.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
      <p className="generated">Generated {new Date(data.generatedAt).toLocaleString()}</p>
    </section>
  );
}

export function App() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState<string>("");
  const [selectedRunId, setSelectedRunId] = useState<string>("");

  useEffect(() => {
    loadDashboard()
      .then((payload) => {
        setData(payload);
        setSelectedRunId(payload.runs[0]?.id ?? "");
      })
      .catch((caught: unknown) => {
        setError(caught instanceof Error ? caught.message : "Unable to load dashboard data");
      });
  }, []);

  const run = useMemo(() => {
    if (!data) {
      return undefined;
    }
    return data.runs.find((item) => item.id === selectedRunId) ?? data.runs[0];
  }, [data, selectedRunId]);

  if (error) {
    return (
      <main className="state-page">
        <h1>Zweig Super Model</h1>
        <p>{error}</p>
        <code>uv run zweig --config configs/default.toml --output artifacts/latest</code>
      </main>
    );
  }

  if (!data || !run) {
    return (
      <main className="state-page">
        <h1>Zweig Super Model</h1>
        <p>Loading dashboard data</p>
      </main>
    );
  }

  const equityLines = [
    { label: "Strategy", color: "#1f7a8c", values: run.monthly.map((point) => point.equity) },
    {
      label: "Benchmark",
      color: "#d88c2d",
      values: run.monthly.map((point) => point.benchmark_equity),
    },
  ];
  const drawdownLines = [
    { label: "Strategy", color: "#9b2c2c", values: run.monthly.map((point) => point.drawdown) },
    {
      label: "Benchmark",
      color: "#5b6770",
      values: run.monthly.map((point) => point.benchmark_drawdown),
    },
  ];

  return (
    <main>
      <header className="app-header">
        <div>
          <p className="eyebrow">Market Timing Research</p>
          <h1>Zweig Super Model</h1>
        </div>
        <label className="run-select">
          <span>Run</span>
          <select value={run.id} onChange={(event) => setSelectedRunId(event.target.value)}>
            {data.runs.map((item) => (
              <option key={item.id} value={item.id}>
                {labelRun(item)}
              </option>
            ))}
          </select>
        </label>
      </header>

      <SummaryGrid run={run} />

      <section className="main-grid">
        <LineChart title="Equity Curve" lines={equityLines} />
        <div className="side-stack">
          <ComponentSnapshot run={run} />
          <Notes data={data} />
        </div>
      </section>

      <section className="main-grid lower">
        <div className="wide-stack">
          <LineChart title="Drawdown" lines={drawdownLines} height={190} percent />
          <ScoreChart points={run.scoreTimeline} />
          <ExposureStrip points={run.monthly} />
        </div>
        <SignalsTable run={run} />
      </section>
    </main>
  );
}
