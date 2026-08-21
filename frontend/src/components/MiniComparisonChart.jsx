import {
  Bar,
  ComposedChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { buildComparisonModel } from '../utils/comparisonData';
import './MiniComparisonChart.css';

const CRITERIA_COLORS = ['#3858a9', '#5f8fc4', '#83b8a5', '#c58a2b', '#b26a8f', '#6f6fae'];

function MiniTooltip({ active, payload, label }) {
  if (!active || !payload?.length || label === '…') return null;
  return (
    <div className="mini-comparison-tooltip">
      <strong>{label}</strong>
      {payload.map((entry) => (
        <span key={entry.dataKey}>
          {entry.name}: {entry.value}
        </span>
      ))}
    </div>
  );
}

function shortenAttempt(value) {
  if (value === '…' || value.length <= 8) return value;
  return `${value.slice(0, 7)}…`;
}

export default function MiniComparisonChart({ results, selectedAnswerId }) {
  const { displayed, criteria, chartData, maxTotalScore } = buildComparisonModel(results, {
    selectedId: selectedAnswerId,
  });
  const selectedResult = displayed.find((result) => result.answerId === selectedAnswerId);
  const selectedAttempt = selectedResult?.name;

  return (
    <section className="mini-comparison-chart" aria-labelledby="mini-comparison-chart-title">
      <div className="mini-comparison-chart-header">
        <strong id="mini-comparison-chart-title">점수 흐름</strong>
        <span>항목별 누적 점수</span>
      </div>
      <div className="mini-comparison-chart-canvas">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 5, right: 4, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="attempt"
              tickFormatter={shortenAttempt}
              tick={{ fontSize: 9, fill: '#6a7280' }}
              tickLine={false}
              axisLine={{ stroke: '#dfe6ee' }}
              height={20}
            />
            <YAxis
              width={24}
              domain={[0, maxTotalScore]}
              allowDecimals={false}
              tick={{ fontSize: 9, fill: '#6a7280' }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<MiniTooltip />} />
            {chartData.some((item) => item.isGap) && (
              <ReferenceLine x="…" stroke="#b8c1d2" strokeDasharray="3 3" />
            )}
            {selectedAttempt && (
              <ReferenceLine x={selectedAttempt} stroke="#d45d3d" strokeDasharray="2 2" />
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
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="mini-comparison-legend" aria-label="그래프 범례">
        {criteria.map((criterion, index) => (
          <span key={criterion}>
            <i style={{ backgroundColor: CRITERIA_COLORS[index % CRITERIA_COLORS.length] }} />
            {criterion}
          </span>
        ))}
      </div>
    </section>
  );
}
