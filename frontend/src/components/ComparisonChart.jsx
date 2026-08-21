import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { buildComparisonModel } from '../utils/comparisonData';
import './ComparisonChart.css';

const CRITERIA_COLORS = ['#3858a9', '#5f8fc4', '#83b8a5', '#c58a2b', '#b26a8f', '#6f6fae'];

function formatLegend(value) {
  return value === 'total' ? '총점' : value;
}

function formatTooltip(value, name) {
  return [value, name === 'total' ? '총점' : name];
}

export default function ComparisonChart({ results }) {
  const { criteria, chartData } = buildComparisonModel(results);

  return (
    <section className="comparison-chart-card" aria-labelledby="comparison-chart-title">
      <div className="comparison-chart-header">
        <div>
          <h2 id="comparison-chart-title">점수 추이</h2>
          <p>항목별 점수는 누적 막대, 총점은 꺾은선으로 표시합니다.</p>
        </div>
      </div>
      <div className="comparison-chart">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 12, right: 18, bottom: 12, left: 0 }}>
            <CartesianGrid stroke="#dfe6ee" strokeDasharray="3 3" />
            <XAxis dataKey="attempt" interval={0} angle={-20} textAnchor="end" height={58} />
            <YAxis allowDecimals={false} />
            <Tooltip formatter={formatTooltip} />
            <Legend formatter={formatLegend} />
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
    </section>
  );
}
