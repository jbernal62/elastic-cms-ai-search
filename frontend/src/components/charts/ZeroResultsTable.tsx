import { AlertTriangle } from "lucide-react";
import type { ZeroResultQuery } from "../../api/client";

interface Props {
  data: ZeroResultQuery[];
}

export default function ZeroResultsTable({ data }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-5 h-5 text-amber-500" />
        <h3 className="font-semibold text-gray-900">
          Zero-Result Queries
        </h3>
        <span className="ml-auto text-xs text-gray-400">
          Content gap opportunities
        </span>
      </div>
      <div className="overflow-auto max-h-[300px]">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-white">
            <tr className="border-b border-gray-200 text-left">
              <th className="py-2 pr-4 font-medium text-gray-500">Query</th>
              <th className="py-2 pr-4 font-medium text-gray-500 text-right">
                Count
              </th>
              <th className="py-2 font-medium text-gray-500">Last Seen</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr
                key={row.query}
                className="border-b border-gray-50 hover:bg-gray-50"
              >
                <td className="py-2 pr-4 text-gray-900 font-medium">
                  {row.query}
                </td>
                <td className="py-2 pr-4 text-right">
                  <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-medium">
                    {row.count}
                  </span>
                </td>
                <td className="py-2 text-gray-400 text-xs">
                  {row.last_seen
                    ? new Date(row.last_seen).toLocaleDateString()
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.length === 0 && (
        <p className="text-center py-8 text-gray-400">
          No zero-result queries yet
        </p>
      )}
    </div>
  );
}
