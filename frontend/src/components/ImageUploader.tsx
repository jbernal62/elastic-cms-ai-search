import { useCallback, useState } from "react";
import { Upload, X } from "lucide-react";

interface Props {
  onUpload: (file: File) => void;
  loading?: boolean;
}

export default function ImageUploader({ onUpload, loading }: Props) {
  const [preview, setPreview] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFile = useCallback(
    (file: File) => {
      if (!file.type.startsWith("image/")) return;
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target?.result as string);
      reader.readAsDataURL(file);
      onUpload(file);
    },
    [onUpload]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const clearPreview = () => {
    setPreview(null);
  };

  return (
    <div className="w-full">
      {preview ? (
        <div className="relative inline-block">
          <img
            src={preview}
            alt="Upload preview"
            className="max-h-64 rounded-xl border border-gray-200 shadow-sm"
          />
          <button
            onClick={clearPreview}
            className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600"
          >
            <X className="w-4 h-4" />
          </button>
          {loading && (
            <div className="absolute inset-0 bg-black/40 rounded-xl flex items-center justify-center">
              <div className="text-white font-medium">Searching...</div>
            </div>
          )}
        </div>
      ) : (
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          className={`flex flex-col items-center justify-center w-full h-64 border-2 border-dashed rounded-xl cursor-pointer transition-colors ${
            dragActive
              ? "border-indigo-500 bg-indigo-50"
              : "border-gray-300 bg-white hover:border-gray-400 hover:bg-gray-50"
          }`}
        >
          <Upload
            className={`w-12 h-12 mb-3 ${
              dragActive ? "text-indigo-500" : "text-gray-400"
            }`}
          />
          <p className="text-sm text-gray-600 font-medium">
            Drop an image here or click to upload
          </p>
          <p className="text-xs text-gray-400 mt-1">
            JPG, PNG, WebP supported
          </p>
          <input
            type="file"
            accept="image/*"
            onChange={handleChange}
            className="hidden"
          />
        </label>
      )}
    </div>
  );
}
