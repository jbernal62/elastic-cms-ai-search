import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  ExternalLink,
  Eye,
  Download,
  Calendar,
  MapPin,
  User,
  Tag,
} from "lucide-react";
import RecommendationPanel from "../components/RecommendationPanel";
import {
  getContent,
  getRelatedContent,
  getRecommendations,
} from "../api/client";
import type { ContentDetail, SearchResult } from "../api/client";

export default function ContentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [content, setContent] = useState<ContentDetail | null>(null);
  const [related, setRelated] = useState<SearchResult[]>([]);
  const [recommended, setRecommended] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      getContent(id),
      getRelatedContent(id),
      getRecommendations(id),
    ])
      .then(([contentData, relatedData, recsData]) => {
        setContent(contentData);
        setRelated(relatedData.results);
        setRecommended(recsData.results);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="text-center py-20 text-gray-400">
        Loading content...
      </div>
    );
  }

  if (!content) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-400 mb-4">Content not found</p>
        <Link to="/" className="text-indigo-600 hover:underline">
          Back to search
        </Link>
      </div>
    );
  }

  return (
    <div>
      {/* Back link */}
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to search
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main content */}
        <div className="lg:col-span-2">
          {/* Preview */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-6">
            {content.content_type === "image" && content.thumbnail_url && (
              <img
                src={content.url || content.thumbnail_url}
                alt={content.title}
                className="w-full max-h-[500px] object-contain bg-gray-50"
              />
            )}
            {content.content_type === "video" && content.thumbnail_url && (
              <div className="relative">
                <img
                  src={content.thumbnail_url}
                  alt={content.title}
                  className="w-full max-h-[400px] object-cover"
                />
                <div className="absolute inset-0 flex items-center justify-center bg-black/30">
                  <div className="w-16 h-16 bg-white/90 rounded-full flex items-center justify-center">
                    <div className="w-0 h-0 border-t-8 border-b-8 border-l-12 border-transparent border-l-gray-800 ml-1" />
                  </div>
                </div>
              </div>
            )}
            {content.content_type === "audio" && (
              <div className="p-8 flex items-center justify-center bg-gradient-to-r from-green-50 to-teal-50 h-48">
                <div className="text-center">
                  <div className="text-4xl mb-2">🎵</div>
                  <p className="text-gray-600 font-medium">Audio File</p>
                  {content.duration_seconds && (
                    <p className="text-sm text-gray-400">
                      Duration: {Math.floor(content.duration_seconds / 60)}:
                      {String(content.duration_seconds % 60).padStart(2, "0")}
                    </p>
                  )}
                </div>
              </div>
            )}
            {!["image", "video", "audio"].includes(content.content_type) && (
              <div className="p-8 flex items-center justify-center bg-gradient-to-r from-orange-50 to-yellow-50 h-48">
                <div className="text-center">
                  <div className="text-4xl mb-2">📄</div>
                  <p className="text-gray-600 font-medium">
                    {content.content_type.charAt(0).toUpperCase() +
                      content.content_type.slice(1)}
                  </p>
                  <p className="text-sm text-gray-400">
                    {content.file_type?.toUpperCase()}
                  </p>
                </div>
              </div>
            )}

            {/* Title & description */}
            <div className="p-6">
              <h1 className="text-2xl font-bold text-gray-900 mb-3">
                {content.title}
              </h1>
              <p className="text-gray-600 leading-relaxed">
                {content.description}
              </p>
            </div>
          </div>

          {/* Recommendations */}
          <div className="space-y-8">
            <RecommendationPanel
              title="Related Content"
              method="More Like This"
              results={related}
            />
            <RecommendationPanel
              title="Recommended Assets"
              method="Vector Similarity (kNN)"
              results={recommended}
            />
          </div>
        </div>

        {/* Sidebar metadata */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl border border-gray-200 p-6 sticky top-24">
            <h2 className="font-semibold text-gray-900 mb-4">Asset Details</h2>

            <div className="space-y-4 text-sm">
              <div className="flex items-start gap-3">
                <Tag className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
                <div>
                  <p className="text-gray-500 mb-1">Content Type</p>
                  <span className="inline-block px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded text-xs font-medium">
                    {content.content_type}
                  </span>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <User className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
                <div>
                  <p className="text-gray-500 mb-1">Author</p>
                  <p className="text-gray-900">{content.author}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Calendar className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
                <div>
                  <p className="text-gray-500 mb-1">Created</p>
                  <p className="text-gray-900">
                    {content.created_at
                      ? new Date(content.created_at).toLocaleDateString()
                      : "N/A"}
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <MapPin className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
                <div>
                  <p className="text-gray-500 mb-1">Region</p>
                  <p className="text-gray-900">{content.region}</p>
                </div>
              </div>

              <div className="flex gap-6">
                <div className="flex items-center gap-1 text-gray-600">
                  <Eye className="w-4 h-4" />
                  {content.view_count?.toLocaleString()} views
                </div>
                <div className="flex items-center gap-1 text-gray-600">
                  <Download className="w-4 h-4" />
                  {content.download_count?.toLocaleString()} downloads
                </div>
              </div>

              {/* Tags */}
              <div>
                <p className="text-gray-500 mb-2">Tags</p>
                <div className="flex flex-wrap gap-1">
                  {content.tags?.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-600"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Source info */}
              <div className="pt-4 border-t border-gray-100">
                <p className="text-gray-500 mb-1">Source</p>
                <p className="text-gray-900 capitalize">{content.source}</p>
                <p className="text-xs text-gray-400 mt-1">
                  {content.license}
                </p>
              </div>

              {/* Link to original */}
              {content.url && (
                <a
                  href={content.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-indigo-600 hover:text-indigo-700 font-medium mt-2"
                >
                  <ExternalLink className="w-4 h-4" />
                  View Original
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
