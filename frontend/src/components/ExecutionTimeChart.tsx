interface ChartRow {
  key: string;
  label: string;
  seconds: number;
}

interface ExecutionTimeChartProps {
  rows: ChartRow[];
}

export function ExecutionTimeChart({ rows }: ExecutionTimeChartProps) {
  if (rows.length === 0) {
    return null;
  }

  const maxValue = Math.max(...rows.map((row) => row.seconds), 1);

  return (
    <div className="time-chart">
      {rows.map((row) => {
        const percent = Math.max(4, Math.round((row.seconds / maxValue) * 100));
        return (
          <div className="time-chart__row" key={row.key}>
            <div className="time-chart__label">{row.label}</div>
            <div className="time-chart__bar-wrap">
              <div className="time-chart__bar" style={{ width: `${percent}%` }} />
            </div>
            <div className="time-chart__value">{row.seconds.toFixed(2)}s</div>
          </div>
        );
      })}
    </div>
  );
}
