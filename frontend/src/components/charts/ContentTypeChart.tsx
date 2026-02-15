import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { ContentTypeBreakdown } from "../../api/client";

const COLORS = [
  "#6366f1",
  "#8b5cf6",
  "#ec4899",
  "#f97316",
  "#10b981",
  "#06b6d4",
  "#eab308",
  "#ef4444",
];

interface Props {
  data: ContentTypeBreakdown[];
}

export default function ContentTypeChart({ data }: Props) {
  const chartData = data.map((d) => ({
    name: d.content_type,
    value: d.count,
    views: d.total_views,
  }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="font-semibold text-gray-900 mb-4">
        Content Type Distribution
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            paddingAngle={2}
            dataKey="value"
            label={({ name, percent }) =>
              `${name} (${(percent * 100).toFixed(0)}%)`
            }
            labelLine={false}
          >
            {chartData.map((_, i) => (
              <Cell
                key={`cell-${i}`}
                fill={COLORS[i % COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number, name: string, props: any) => [
              `${value} items (${props.payload.views.toLocaleString()} views)`,
              name,
            ]}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
