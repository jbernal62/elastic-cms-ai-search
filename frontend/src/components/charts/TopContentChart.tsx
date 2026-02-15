import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { SearchResult } from "../../api/client";

interface Props {
  data: SearchResult[];
}

export default function TopContentChart({ data }: Props) {
  const chartData = data.slice(0, 10).map((d) => ({
    name: d.title?.length > 30 ? d.title.slice(0, 30) + "..." : d.title,
    views: d.view_count,
    type: d.content_type,
  }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="font-semibold text-gray-900 mb-4">
        Most Viewed Content
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 120 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" />
          <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(value: number) => [value.toLocaleString(), "Views"]}
          />
          <Bar dataKey="views" fill="#6366f1" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
