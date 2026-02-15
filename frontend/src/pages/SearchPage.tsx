import { useState } from "react";
import { Clock, Filter } from "lucide-react";
import SearchBar from "../components/SearchBar";
import ResultCard from "../components/ResultCard";
import { hybridSearch, logClick } from "../api/client";
import type { SearchResult } from "../api/client";

const CONTENT_TYPES = [
  "all",
  "image",
  "video",
  "audio",
  "article",
  "paper",
  "book",
  "document",
];

export default function SearchPage() {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [meta, setMeta] = useState<{
    query: string;
    total: number;
    time: number;
  } | null>(null);
  const [selectedType, setSelectedType] = useState("all");
  const [showFilters, setShowFilters] = useState(false);

  const handleSearch = async (query: string) => {
    setLoading(true);
    try {
      const contentType =
        selectedType === "all" ? undefined : selectedType;
      const resp = await hybridSearch(query, {
        content_type: contentType,
      });
      setResults(resp.results);
      setMeta({
        query: resp.query,
        total: resp.total,
        time: resp.response_time_ms,
      });
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          AI-Powered Content Search
        </h1>
        <p className="text-gray-500">
          Search across 2,000+ assets using natural language. Powered by
          Elasticsearch hybrid search (BM25 + vectors + RRF).
        </p>
      </div>

      {/* Search bar */}
      <div className="max-w-3xl mx-auto mb-6">
        <SearchBar onSearch={handleSearch} loading={loading} />
      </div>

      {/* Filters */}
      <div className="max-w-3xl mx-auto mb-8">
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <Filter className="w-4 h-4" />
          Filters
        </button>
        {showFilters && (
          <div className="mt-3 flex flex-wrap gap-2">
            {CONTENT_TYPES.map((t) => (
              <button
                key={t}
                onClick={() => setSelectedType(t)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition ${
                  selectedType === t
                    ? "bg-indigo-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Results meta */}
      {meta && (
        <div className="flex items-center gap-4 mb-4 text-sm text-gray-500">
          <span>
            <strong className="text-gray-900">{meta.total}</strong> results for
            &ldquo;{meta.query}&rdquo;
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            {meta.time}ms
          </span>
        </div>
      )}

      {/* Results grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {results.map((r) => (
          <ResultCard
            key={r.id}
            result={r}
            onClickLog={() => logClick(r.id, meta?.query)}
          />
        ))}
      </div>

      {/* Empty state */}
      {!loading && results.length === 0 && meta && (
        <div className="text-center py-12 text-gray-400">
          No results found. Try a different query or adjust filters.
        </div>
      )}
    </div>
  );
}
