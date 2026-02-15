import { useCallback, useEffect, useRef, useState } from "react";
import {
  Upload,
  Trash2,
  ImageIcon,
  FileText,
  Music,
  Video,
  CheckCircle,
  Loader2,
  AlertCircle,
  FolderUp,
} from "lucide-react";
import type { AssetItem } from "../api/client";
import { deleteAsset, listAssets, uploadAsset } from "../api/client";

const typeIcons: Record<string, typeof ImageIcon> = {
  image: ImageIcon,
  video: Video,
  audio: Music,
  document: FileText,
};

const typeBadgeColors: Record<string, string> = {
  image: "bg-blue-100 text-blue-700",
  video: "bg-purple-100 text-purple-700",
  audio: "bg-green-100 text-green-700",
  document: "bg-orange-100 text-orange-700",
};

type UploadStatus = "idle" | "uploading" | "success" | "error";

interface UploadItem {
  file: File;
  status: UploadStatus;
  progress: number;
  error?: string;
  docId?: string;
}

export default function AssetsPage() {
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchAssets = useCallback(async () => {
    try {
      const resp = await listAssets();
      setAssets(resp.assets);
      setTotal(resp.total);
    } catch {
      // silently fail on load
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAssets();
  }, [fetchAssets]);

  const handleFiles = async (files: FileList | File[]) => {
    const fileArray = Array.from(files);
    const newUploads: UploadItem[] = fileArray.map((f) => ({
      file: f,
      status: "uploading" as UploadStatus,
      progress: 0,
    }));

    setUploads((prev) => [...newUploads, ...prev]);

    for (let i = 0; i < fileArray.length; i++) {
      try {
        const resp = await uploadAsset(fileArray[i]);
        setUploads((prev) =>
          prev.map((u) =>
            u.file === fileArray[i]
              ? { ...u, status: "success", progress: 100, docId: resp.doc_id }
              : u
          )
        );
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Upload failed";
        setUploads((prev) =>
          prev.map((u) =>
            u.file === fileArray[i]
              ? { ...u, status: "error", error: message }
              : u
          )
        );
      }
    }

    // Refresh the asset list after all uploads
    setTimeout(fetchAssets, 2000);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleDelete = async (asset: AssetItem) => {
    if (!confirm(`Delete "${asset.title}"?`)) return;
    try {
      await deleteAsset(asset.id);
      setAssets((prev) => prev.filter((a) => a.id !== asset.id));
      setTotal((prev) => prev - 1);
    } catch {
      alert("Failed to delete asset");
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Asset Management</h1>
        <p className="text-gray-500 mt-1">
          Upload images and documents to your GCS bucket. They will be
          automatically embedded and indexed for search.
        </p>
      </div>

      {/* Upload area */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
          dragOver
            ? "border-indigo-400 bg-indigo-50"
            : "border-gray-300 hover:border-indigo-300 hover:bg-gray-50"
        }`}
      >
        <FolderUp
          className={`w-12 h-12 mx-auto mb-4 ${
            dragOver ? "text-indigo-500" : "text-gray-400"
          }`}
        />
        <p className="text-lg font-medium text-gray-700">
          Drop files here or click to browse
        </p>
        <p className="text-sm text-gray-500 mt-1">
          Images, documents, audio, and video files supported
        </p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) handleFiles(e.target.files);
          }}
        />
      </div>

      {/* Upload queue */}
      {uploads.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
            Upload Queue
          </h2>
          {uploads.map((u, idx) => (
            <div
              key={idx}
              className="flex items-center gap-3 bg-white rounded-lg border border-gray-200 p-3"
            >
              {u.status === "uploading" && (
                <Loader2 className="w-5 h-5 text-indigo-500 animate-spin flex-shrink-0" />
              )}
              {u.status === "success" && (
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
              )}
              {u.status === "error" && (
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
              )}
              <span className="text-sm text-gray-700 truncate flex-1">
                {u.file.name}
              </span>
              <span className="text-xs text-gray-400">
                {(u.file.size / 1024).toFixed(0)} KB
              </span>
              {u.status === "success" && (
                <span className="text-xs text-green-600 font-medium">
                  Uploaded — indexing in progress
                </span>
              )}
              {u.status === "error" && (
                <span className="text-xs text-red-600">{u.error}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Asset grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Uploaded Assets{" "}
            <span className="text-gray-400 font-normal">({total})</span>
          </h2>
          <button
            onClick={() => {
              setLoading(true);
              fetchAssets();
            }}
            className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
          </div>
        ) : assets.length === 0 ? (
          <div className="text-center py-20 text-gray-400">
            <Upload className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No uploaded assets yet. Drop files above to get started.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {assets.map((asset) => {
              const Icon = typeIcons[asset.content_type] || FileText;
              const badgeColor =
                typeBadgeColors[asset.content_type] ||
                "bg-gray-100 text-gray-700";

              return (
                <div
                  key={asset.id}
                  className="bg-white rounded-xl border border-gray-200 overflow-hidden group hover:shadow-lg transition-all"
                >
                  {/* Thumbnail */}
                  <div className="relative h-36 bg-gray-100 overflow-hidden">
                    {asset.thumbnail_url ? (
                      <img
                        src={asset.thumbnail_url}
                        alt={asset.title}
                        className="w-full h-full object-cover"
                        loading="lazy"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = "none";
                        }}
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Icon className="w-10 h-10 text-gray-300" />
                      </div>
                    )}
                    <span
                      className={`absolute top-2 right-2 px-2 py-0.5 rounded-full text-xs font-medium ${badgeColor}`}
                    >
                      {asset.content_type}
                    </span>
                    {/* Delete button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(asset);
                      }}
                      className="absolute top-2 left-2 p-1.5 bg-red-500 text-white rounded-lg opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  {/* Info */}
                  <div className="p-3">
                    <h3 className="text-sm font-medium text-gray-900 truncate">
                      {asset.title}
                    </h3>
                    <p className="text-xs text-gray-400 mt-1">
                      {asset.file_type?.toUpperCase()}
                      {asset.width && asset.height
                        ? ` \u00B7 ${asset.width}\u00D7${asset.height}`
                        : ""}
                    </p>
                    {asset.tags?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {asset.tags.slice(0, 2).map((tag) => (
                          <span
                            key={tag}
                            className="px-1.5 py-0.5 bg-gray-100 rounded text-xs text-gray-500"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
