import { useNavigate } from "react-router-dom";
import {
  ImageIcon,
  Video,
  Music,
  FileText,
  BookOpen,
  GraduationCap,
  Eye,
  Download,
} from "lucide-react";
import type { SearchResult } from "../api/client";

const typeIcons: Record<string, typeof ImageIcon> = {
  image: ImageIcon,
  video: Video,
  audio: Music,
  document: FileText,
  article: FileText,
  book: BookOpen,
  paper: GraduationCap,
};

const typeBadgeColors: Record<string, string> = {
  image: "bg-blue-100 text-blue-700",
  video: "bg-purple-100 text-purple-700",
  audio: "bg-green-100 text-green-700",
  document: "bg-orange-100 text-orange-700",
  article: "bg-yellow-100 text-yellow-700",
  book: "bg-red-100 text-red-700",
  paper: "bg-teal-100 text-teal-700",
};

interface Props {
  result: SearchResult;
  highlight?: boolean;
  onClickLog?: () => void;
}

export default function ResultCard({ result, highlight, onClickLog }: Props) {
  const navigate = useNavigate();
  const Icon = typeIcons[result.content_type] || FileText;
  const badgeColor =
    typeBadgeColors[result.content_type] || "bg-gray-100 text-gray-700";

  const handleClick = () => {
    onClickLog?.();
    navigate(`/content/${result.id}`);
  };

  return (
    <div
      onClick={handleClick}
      className={`bg-white rounded-xl border cursor-pointer transition-all hover:shadow-lg hover:-translate-y-0.5 ${
        highlight
          ? "border-indigo-400 ring-2 ring-indigo-100"
          : "border-gray-200"
      }`}
    >
      {/* Thumbnail */}
      <div className="relative h-40 bg-gray-100 rounded-t-xl overflow-hidden">
        {result.thumbnail_url ? (
          <img
            src={result.thumbnail_url}
            alt={result.title}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Icon className="w-12 h-12 text-gray-300" />
          </div>
        )}
        {/* Type badge */}
        <span
          className={`absolute top-2 right-2 px-2 py-0.5 rounded-full text-xs font-medium ${badgeColor}`}
        >
          {result.content_type}
        </span>
        {/* Score badge */}
        {result.score != null && (
          <span className="absolute top-2 left-2 px-2 py-0.5 rounded-full text-xs font-medium bg-black/60 text-white">
            {result.score.toFixed(3)}
          </span>
        )}
      </div>

      {/* Body */}
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 line-clamp-2 mb-1 text-sm">
          {result.title}
        </h3>
        <p className="text-xs text-gray-500 line-clamp-2 mb-3">
          {result.description}
        </p>

        {/* Tags */}
        <div className="flex flex-wrap gap-1 mb-3">
          {result.tags?.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-600"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span className="truncate max-w-[100px]">{result.source}</span>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <Eye className="w-3 h-3" />
              {result.view_count?.toLocaleString()}
            </span>
            <span className="flex items-center gap-1">
              <Download className="w-3 h-3" />
              {result.download_count?.toLocaleString()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
