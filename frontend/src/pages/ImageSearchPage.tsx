import { useState } from "react";
import { Clock, ImageIcon, Type } from "lucide-react";
import ImageUploader from "../components/ImageUploader";
import SearchBar from "../components/SearchBar";
import ResultCard from "../components/ResultCard";
import { imageSearch, textToImageSearch } from "../api/client";
import type { SearchResult } from "../api/client";

type SearchMode = "upload" | "text";

export default function ImageSearchPage() {
  const [mode, setMode] = useState<SearchMode>("upload");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [meta, setMeta] = useState<{
    query: string;
    total: number;
    time: number;
  } | null>(null);

  const handleUpload = async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await imageSearch(file);
      setResults(resp.results);
      setMeta({
        query: resp.query,
        total: resp.total,
        time: resp.response_time_ms,
      });
    } catch (err: any) {
      console.error("Image search failed:", err);
      if (err?.response?.status === 413) {
        setError("Image is too large. Please upload a smaller image (under 25 MB).");
      } else if (err?.code === "ECONNABORTED") {
        setError("Search timed out. Please try a smaller image.");
      } else {
        setError("Image search failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleTextSearch = async (query: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await textToImageSearch(query);
      setResults(resp.results);
      setMeta({
        query: resp.query,
        total: resp.total,
        time: resp.response_time_ms,
      });
    } catch (err: any) {
      console.error("Text-to-image search failed:", err);
      setError("Text-to-image search failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleModeChange = (newMode: SearchMode) => {
    setMode(newMode);
    setResults([]);
    setMeta(null);
    setError(null);
  };

  return (
    <div>
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Visual Similarity Search
        </h1>
        <p className="text-gray-500">
          Find visually similar content using CLIP embeddings — upload an image
          or describe what you're looking for in text.
        </p>
      </div>

      {/* Mode toggle */}
      <div className="max-w-lg mx-auto mb-6">
        <div className="flex rounded-xl border border-gray-200 overflow-hidden">
          <button
            onClick={() => handleModeChange("upload")}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium transition ${
              mode === "upload"
                ? "bg-indigo-600 text-white"
                : "bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            <ImageIcon className="w-4 h-4" />
            Upload Image
          </button>
          <button
            onClick={() => handleModeChange("text")}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium transition ${
              mode === "text"
                ? "bg-indigo-600 text-white"
                : "bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            <Type className="w-4 h-4" />
            Text Description
          </button>
        </div>
      </div>

      {/* Upload area */}
      {mode === "upload" && (
        <div className="max-w-lg mx-auto mb-8">
          <ImageUploader onUpload={handleUpload} loading={loading} />
        </div>
      )}

      {/* Text search area */}
      {mode === "text" && (
        <div className="max-w-3xl mx-auto mb-8">
          <SearchBar
            onSearch={handleTextSearch}
            loading={loading}
            placeholder="Describe an image, e.g. 'sunset over mountains' or 'dog playing in snow'"
          />
          <p className="text-xs text-gray-400 mt-2 text-center">
            Uses CLIP cross-modal embeddings to search images by text description
          </p>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="max-w-lg mx-auto mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Results meta */}
      {meta && (
        <div className="flex items-center gap-4 mb-4 text-sm text-gray-500">
          <span>
            <strong className="text-gray-900">{meta.total}</strong> visually
            similar results
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
          <ResultCard key={r.id} result={r} />
        ))}
      </div>

      {/* Empty state */}
      {!loading && results.length === 0 && !meta && (
        <div className="text-center py-12 text-gray-400">
          {mode === "upload"
            ? "Upload an image above to find similar content across your CMS."
            : "Enter a text description above to find matching images."}
        </div>
      )}
    </div>
  );
}
