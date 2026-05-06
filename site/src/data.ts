export type Stats = {
  start: string;
  end: string;
  periods: number;
  final_equity: number;
  total_return: number;
  cagr: number;
  annualized_volatility: number;
  sharpe: number;
  max_drawdown: number;
  average_exposure: number;
  percent_periods_invested: number;
  exposure_changes: number;
  invested_period_wins: number;
  invested_period_losses: number;
};

export type MonthlyPoint = {
  date: string;
  close: number;
  asset_return: number;
  strategy_return: number;
  benchmark_return: number;
  signal_exposure: number;
  applied_exposure: number;
  equity: number;
  benchmark_equity: number;
  drawdown: number;
  benchmark_drawdown: number;
};

export type ScorePoint = {
  date: string;
  monetary_points?: number;
  four_percent_points?: number;
  points?: number;
  state?: string;
  signal?: string | null;
  exposure?: number;
  book_partial_exposure?: number;
};

export type SettingValue = string | number | boolean | null;

export type ModelSettings = Record<string, Record<string, SettingValue>>;

export type DashboardRun = {
  id: string;
  scenarioId: string;
  scenarioName: string;
  scenarioDescription: string;
  settings: ModelSettings;
  target: string;
  model: string;
  strategy: Stats;
  benchmark: Stats;
  monthly: MonthlyPoint[];
  investedPeriods: Array<Record<string, string | number | null>>;
  scoreTimeline: ScorePoint[];
  signals: ScorePoint[];
};

export type DashboardScenario = {
  id: string;
  name: string;
  description: string;
  settings: ModelSettings;
};

export type DashboardPayload = {
  generatedAt: string;
  title: string;
  notes: string[];
  scenarios: DashboardScenario[];
  runs: DashboardRun[];
  components: Record<string, Array<Record<string, string | number | boolean | null>>>;
};

export async function loadDashboard(): Promise<DashboardPayload> {
  const response = await fetch(`${import.meta.env.BASE_URL}data/dashboard.json`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Unable to load dashboard data (${response.status})`);
  }

  return (await response.json()) as DashboardPayload;
}
