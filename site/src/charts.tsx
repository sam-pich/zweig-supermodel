import type { MonthlyPoint, ScorePoint } from "./data";

type Line = {
  label: string;
  values: number[];
  color: string;
};

function formatCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `${(value / 1_000).toFixed(0)}K`;
  }
  return value.toFixed(0);
}

function pointsToPath(values: number[], min: number, max: number, width: number, height: number): string {
  if (!values.length) {
    return "";
  }
  const span = max - min || 1;
  return values
    .map((value, index) => {
      const x = values.length === 1 ? 0 : (index / (values.length - 1)) * width;
      const y = height - ((value - min) / span) * height;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

function tickIndexes(length: number, maxTicks = 7): number[] {
  if (length <= 0) {
    return [];
  }
  if (length === 1) {
    return [0];
  }

  const ticks = new Set<number>();
  const count = Math.min(maxTicks, length);
  for (let index = 0; index < count; index += 1) {
    ticks.add(Math.round((index / (count - 1)) * (length - 1)));
  }
  return [...ticks].sort((left, right) => left - right);
}

function tickLabel(date: string): string {
  return date.slice(0, 4);
}

export function LineChart({
  title,
  lines,
  dates,
  height = 260,
  percent = false,
}: {
  title: string;
  lines: Line[];
  dates: string[];
  height?: number;
  percent?: boolean;
}) {
  const width = 900;
  const values = lines.flatMap((line) => line.values);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const yTicks = [max, min + (max - min) / 2, min];
  const xTicks = tickIndexes(dates.length);

  return (
    <section className="panel chart-panel">
      <div className="panel-head">
        <h2>{title}</h2>
        <div className="legend">
          {lines.map((line) => (
            <span key={line.label}>
              <i style={{ background: line.color }} />
              {line.label}
            </span>
          ))}
        </div>
      </div>
      <div className="chart-frame">
        <div className="axis-labels">
          {yTicks.map((tick) => (
            <span key={tick}>{percent ? `${(tick * 100).toFixed(0)}%` : formatCompact(tick)}</span>
          ))}
        </div>
        <div className="plot-area">
          <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
            <g className="grid">
              {[0, 0.5, 1].map((position) => (
                <line
                  key={position}
                  x1="0"
                  x2={width}
                  y1={height * position}
                  y2={height * position}
                />
              ))}
              {xTicks.map((index) => {
                const x = dates.length === 1 ? 0 : (index / (dates.length - 1)) * width;
                return <line key={dates[index]} x1={x} x2={x} y1="0" y2={height} />;
              })}
            </g>
            {lines.map((line) => (
              <path
                key={line.label}
                d={pointsToPath(line.values, min, max, width, height)}
                fill="none"
                stroke={line.color}
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            ))}
          </svg>
          <div className="x-axis" aria-label={`${title} time axis`}>
            {xTicks.map((index) => (
              <span
                key={dates[index]}
                style={{ left: `${dates.length === 1 ? 0 : (index / (dates.length - 1)) * 100}%` }}
              >
                {tickLabel(dates[index])}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

export function ScoreChart({ points }: { points: ScorePoint[] }) {
  const width = 900;
  const height = 180;
  const values = points.map((point) => point.points ?? 0);
  const monetary = points.map((point) => point.monetary_points ?? 0);
  const dates = points.map((point) => point.date);
  const xTicks = tickIndexes(dates.length);

  return (
    <section className="panel chart-panel">
      <div className="panel-head">
        <h2>Model Score</h2>
        <div className="legend">
          <span>
            <i style={{ background: "#1f7a8c" }} />
            Super
          </span>
          <span>
            <i style={{ background: "#d88c2d" }} />
            Monetary
          </span>
        </div>
      </div>
      <div className="chart-frame score-chart">
        <div className="axis-labels">
          <span>10</span>
          <span>5</span>
          <span>0</span>
        </div>
        <div className="plot-area">
          <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Model score">
            <g className="grid">
              {[0, 0.4, 0.7, 1].map((position) => (
                <line
                  key={position}
                  x1="0"
                  x2={width}
                  y1={height * position}
                  y2={height * position}
                />
              ))}
              {xTicks.map((index) => {
                const x = dates.length === 1 ? 0 : (index / (dates.length - 1)) * width;
                return <line key={dates[index]} x1={x} x2={x} y1="0" y2={height} />;
              })}
            </g>
            <line
              className="threshold buy"
              x1="0"
              x2={width}
              y1={height * 0.4}
              y2={height * 0.4}
            />
            <line
              className="threshold sell"
              x1="0"
              x2={width}
              y1={height * 0.7}
              y2={height * 0.7}
            />
            <path
              d={pointsToPath(values, 0, 10, width, height)}
              fill="none"
              stroke="#1f7a8c"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d={pointsToPath(monetary, 0, 10, width, height)}
              fill="none"
              stroke="#d88c2d"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <div className="x-axis" aria-label="Model score time axis">
            {xTicks.map((index) => (
              <span
                key={dates[index]}
                style={{ left: `${dates.length === 1 ? 0 : (index / (dates.length - 1)) * 100}%` }}
              >
                {tickLabel(dates[index])}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

export function ExposureStrip({ points }: { points: MonthlyPoint[] }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Exposure</h2>
      </div>
      <div className="exposure-strip" aria-label="Monthly exposure strip">
        {points.map((point) => (
          <span
            key={point.date}
            title={`${point.date}: ${(point.applied_exposure * 100).toFixed(0)}%`}
            style={{
              opacity: 0.18 + point.applied_exposure * 0.82,
              background: point.applied_exposure > 0 ? "#1f7a8c" : "#d9dee2",
            }}
          />
        ))}
      </div>
    </section>
  );
}
