import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { GeoRegion } from "../../api/client";

interface Props {
  data: GeoRegion[];
}

export default function GeoHeatmap({ data }: Props) {
  const chartData = data
    .sort((a, b) => b.search_count - a.search_count)
    .map((d) => ({
      region: d.region,
      searches: d.search_count,
      topQueries: d.top_queries.join(", "),
    }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="font-semibold text-gray-900 mb-4">
        Geographic Distribution
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="region" tick={{ fontSize: 11 }} />
          <YAxis />
          <Tooltip
            formatter={(value: number) => [value.toLocaleString(), "Searches"]}
            labelFormatter={(label) => {
              const item = chartData.find((d) => d.region === label);
              return `${label}\nTop: ${item?.topQueries || "N/A"}`;
            }}
          />
          <Bar dataKey="searches" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      {/* Top queries per region */}
      <div className="mt-4 grid grid-cols-2 gap-2">
        {data.slice(0, 4).map((d) => (
          <div key={d.region} className="text-xs p-2 bg-gray-50 rounded">
            <span className="font-medium text-gray-700">{d.region}:</span>{" "}
            <span className="text-gray-500">
              {d.top_queries.slice(0, 3).join(", ")}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
