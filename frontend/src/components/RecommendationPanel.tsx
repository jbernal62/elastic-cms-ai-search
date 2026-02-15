import { useNavigate } from "react-router-dom";
import type { SearchResult } from "../api/client";

interface Props {
  title: string;
  method: string;
  results: SearchResult[];
}

export default function RecommendationPanel({ title, method, results }: Props) {
  const navigate = useNavigate();

  if (!results.length) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">{title}</h3>
        <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
          {method}
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {results.map((r) => (
          <div
            key={r.id}
            onClick={() => navigate(`/content/${r.id}`)}
            className="bg-white border border-gray-200 rounded-lg cursor-pointer hover:shadow-md transition overflow-hidden"
          >
            {r.thumbnail_url ? (
              <img
                src={r.thumbnail_url}
                alt={r.title}
                className="w-full h-24 object-cover"
                loading="lazy"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                }}
              />
            ) : (
              <div className="w-full h-24 bg-gray-100" />
            )}
            <div className="p-2">
              <p className="text-xs font-medium text-gray-800 line-clamp-2">
                {r.title}
              </p>
              <p className="text-[10px] text-gray-400 mt-1">
                {r.content_type} &middot; {r.source}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
