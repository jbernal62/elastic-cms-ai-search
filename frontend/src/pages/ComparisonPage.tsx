import { useState } from "react";
import { Clock, Sparkles, Type } from "lucide-react";
import SearchBar from "../components/SearchBar";
import ResultCard from "../components/ResultCard";
import { compareSearch } from "../api/client";
import type { CompareResponse } from "../api/client";

export default function ComparisonPage() {
  const [data, setData] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (query: string) => {
    setLoading(true);
    try {
      const resp = await compareSearch(query);
      setData(resp);
    } catch (err) {
      console.error("Comparison search failed:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Keyword vs AI Hybrid Search
        </h1>
        <p className="text-gray-500">
          Compare traditional keyword search (BM25) against hybrid AI search
          (BM25 + vectors + RRF) side by side.
        </p>
      </div>

      {/* Search bar */}
      <div className="max-w-3xl mx-auto mb-8">
        <SearchBar
          onSearch={handleSearch}
          loading={loading}
          placeholder="Try: 'golden hour landscape' or 'sustainable energy innovations'"
        />
      </div>

      {/* Meta */}
      {data && (
        <div className="flex items-center justify-center gap-4 mb-6 text-sm text-gray-500">
          <span>Query: &ldquo;{data.query}&rdquo;</span>
          <span className="flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            {data.response_time_ms}ms
          </span>
          {data.hybrid_only_ids.length > 0 && (
            <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-full text-xs font-medium">
              {data.hybrid_only_ids.length} semantic-only results
            </span>
          )}
        </div>
      )}

      {/* Side-by-side columns */}
      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Keyword column */}
          <div>
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-200">
              <Type className="w-5 h-5 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-800">
                Keyword Search (BM25)
              </h2>
              <span className="ml-auto text-sm text-gray-400">
                {data.keyword.total} results
              </span>
            </div>
            <div className="space-y-3">
              {data.keyword.results.map((r) => (
                <ResultCard key={r.id} result={r} />
              ))}
              {data.keyword.results.length === 0 && (
                <p className="text-center text-gray-400 py-8">
                  No keyword results
                </p>
              )}
            </div>
          </div>

          {/* Hybrid column */}
          <div>
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-indigo-200">
              <Sparkles className="w-5 h-5 text-indigo-600" />
              <h2 className="text-lg font-semibold text-indigo-800">
                AI Hybrid Search (BM25 + Vectors)
              </h2>
              <span className="ml-auto text-sm text-gray-400">
                {data.hybrid.total} results
              </span>
            </div>
            <div className="space-y-3">
              {data.hybrid.results.map((r) => (
                <ResultCard
                  key={r.id}
                  result={r}
                  highlight={data.hybrid_only_ids.includes(r.id)}
                />
              ))}
              {data.hybrid.results.length === 0 && (
                <p className="text-center text-gray-400 py-8">
                  No hybrid results
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Legend */}
      {data && data.hybrid_only_ids.length > 0 && (
        <div className="mt-6 p-4 bg-indigo-50 rounded-lg text-sm text-indigo-700">
          <strong>Highlighted results</strong> (with indigo border) were found
          only by AI hybrid search — these are semantic matches that keyword
          search missed. This demonstrates the value of vector-based search for
          content discovery.
        </div>
      )}
    </div>
  );
}
