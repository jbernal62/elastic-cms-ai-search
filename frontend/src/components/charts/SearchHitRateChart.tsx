import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { HitRatePoint } from "../../api/client";

interface Props {
  data: HitRatePoint[];
}

export default function SearchHitRateChart({ data }: Props) {
  const chartData = data.map((d) => ({
    date: new Date(d.date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    "Hit Rate %": d.hit_rate,
    "Total Searches": d.total_searches,
  }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="font-semibold text-gray-900 mb-4">
        Search Hit Rate Over Time
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis yAxisId="left" domain={[0, 100]} unit="%" />
          <YAxis yAxisId="right" orientation="right" />
          <Tooltip />
          <Legend />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="Hit Rate %"
            stroke="#6366f1"
            strokeWidth={2}
            dot={false}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="Total Searches"
            stroke="#94a3b8"
            strokeWidth={1}
            dot={false}
            strokeDasharray="4 4"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
