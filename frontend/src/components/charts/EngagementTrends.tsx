import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { EngagementCategory } from "../../api/client";

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
  data: EngagementCategory[];
}

export default function EngagementTrends({ data }: Props) {
  // Pivot data: each date becomes a row with category columns
  const dateMap = new Map<string, Record<string, number>>();
  const categories: string[] = [];

  for (const cat of data) {
    categories.push(cat.category);
    for (const point of cat.trend) {
      const dateKey = new Date(point.date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
      if (!dateMap.has(dateKey)) dateMap.set(dateKey, {});
      dateMap.get(dateKey)![cat.category] = point.views;
    }
  }

  const chartData = Array.from(dateMap.entries()).map(([date, values]) => ({
    date,
    ...values,
  }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="font-semibold text-gray-900 mb-4">
        Engagement Trends by Category
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis />
          <Tooltip />
          <Legend />
          {categories.map((cat, i) => (
            <Area
              key={cat}
              type="monotone"
              dataKey={cat}
              stackId="1"
              stroke={COLORS[i % COLORS.length]}
              fill={COLORS[i % COLORS.length]}
              fillOpacity={0.4}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
