import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { buildComparisonModel, COMPARISON_LABEL_WIDTH } from '../utils/comparisonData';
import './ComparisonChart.css';

const CRITERIA_COLORS = ['#3858a9', '#5f8fc4', '#83b8a5', '#c58a2b', '#b26a8f', '#6f6fae'];

function formatLabel(value) {
  return value === 'total' ? '총점' : value;
}

function ComparisonTooltip({ active, payload, label }) {
  if (!active || !payload?.length || label === '…') return null;

  return (
    <div className="comparison-chart-tooltip">
      <strong>{label}</strong>
      {payload.map((entry) => (
        <span key={entry.dataKey}>
          {formatLabel(entry.name)}: {entry.value}
        </span>
      ))}
    </div>
  );
}

function ComparisonLegend({ criteria }) {
  const entries = [
    ...criteria.map((criterion, index) => ({
      key: `criterion-${index}`,
      label: criterion,
      color: CRITERIA_COLORS[index % CRITERIA_COLORS.length],
    })),
    { key: 'total', label: '총점', color: '#d45d3d' },
  ];

  return (
    <div className="comparison-chart-legend" aria-label="그래프 범례">
      {entries.map((entry) => (
        <span className="comparison-chart-legend-item" key={entry.key} title={entry.label}>
          <i style={{ backgroundColor: entry.color }} />
          {entry.label}
        </span>
      ))}
    </div>
  );
}

export default function ComparisonChart({ results, truncate = true }) {
  const { criteria, chartData, hiddenMiddleCount, maxTotalScore } = buildComparisonModel(results, {
    truncate,
  });

  return (
    <section className="comparison-chart-card" aria-labelledby="comparison-chart-title">
      <div className="comparison-chart-header">
        <div>
          <h2 id="comparison-chart-title">점수 추이</h2>
          <p>
            항목별 점수는 누적 막대, 총점은 꺾은선으로 표시합니다.
            {hiddenMiddleCount > 0 && ' … 표시된 지점은 중간 회차를 생략한 구간입니다.'}
          </p>
        </div>
      </div>
      <div className="comparison-chart">
        <div className="comparison-chart-canvas">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 12, right: 0, bottom: 12, left: 0 }}>
              <CartesianGrid stroke="#dfe6ee" strokeDasharray="3 3" />
              <XAxis dataKey="attempt" interval={0} angle={-20} textAnchor="end" height={58} />
              <YAxis
                width={COMPARISON_LABEL_WIDTH}
                domain={[0, maxTotalScore]}
                allowDecimals={false}
              />
              <Tooltip content={<ComparisonTooltip />} />
              {hiddenMiddleCount > 0 && (
                <ReferenceLine
                  x="…"
                  stroke="#9ba7bd"
                  strokeDasharray="4 4"
                  label={{
                    value: `중간 ${hiddenMiddleCount}회차 생략`,
                    position: 'insideTop',
                    fill: '#6a7280',
                    fontSize: 11,
                  }}
                />
              )}
              {criteria.map((criterion, index) => (
                <Bar
                  key={criterion}
                  dataKey={criterion}
                  name={criterion}
                  stackId="criteria"
                  fill={CRITERIA_COLORS[index % CRITERIA_COLORS.length]}
                  isAnimationActive={false}
                />
              ))}
              <Line
                type="monotone"
                dataKey="total"
                name="총점"
                stroke="#d45d3d"
                strokeWidth={3}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
                isAnimationActive={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <ComparisonLegend criteria={criteria} />
      </div>
    </section>
  );
}
