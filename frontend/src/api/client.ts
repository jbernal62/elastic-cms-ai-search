import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

// ─── Search ──────────────────────────────────────────────────────

export interface SearchResult {
  id: string;
  score: number | null;
  title: string;
  description: string;
  content_type: string;
  tags: string[];
  category: string;
  source: string;
  author: string;
  license: string;
  url: string;
  thumbnail_url: string;
  preview_url: string;
  file_type: string;
  created_at: string;
  region: string;
  view_count: number;
  download_count: number;
}

export interface SearchResponse {
  query: string;
  search_type: string;
  total: number;
  response_time_ms: number;
  results: SearchResult[];
}

export interface CompareResponse {
  query: string;
  response_time_ms: number;
  keyword: { total: number; results: SearchResult[] };
  hybrid: { total: number; results: SearchResult[] };
  hybrid_only_ids: string[];
}

export async function hybridSearch(
  q: string,
  filters?: { content_type?: string; category?: string; region?: string }
): Promise<SearchResponse> {
  const params = { q, ...filters };
  const { data } = await api.get("/search", { params });
  return data;
}

export async function keywordSearch(
  q: string,
  filters?: { content_type?: string; category?: string }
): Promise<SearchResponse> {
  const params = { q, ...filters };
  const { data } = await api.get("/search/keyword", { params });
  return data;
}

export async function imageSearch(file: File): Promise<SearchResponse> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/search/image", form, { timeout: 120000 });
  return data;
}

export async function compareSearch(
  q: string,
  filters?: { content_type?: string; category?: string }
): Promise<CompareResponse> {
  const params = { q, ...filters };
  const { data } = await api.get("/search/compare", { params });
  return data;
}

export async function textToImageSearch(
  q: string,
  size: number = 20
): Promise<SearchResponse> {
  const { data } = await api.get("/search/text-to-image", { params: { q, size } });
  return data;
}

// ─── Content ─────────────────────────────────────────────────────

export interface ContentDetail extends SearchResult {
  duration_seconds?: number;
  width?: number;
  height?: number;
}

export async function getContent(id: string): Promise<ContentDetail> {
  const { data } = await api.get(`/content/${id}`);
  return data;
}

export async function getRelatedContent(
  id: string
): Promise<{ results: SearchResult[] }> {
  const { data } = await api.get(`/content/${id}/related`);
  return data;
}

export async function getRecommendations(
  id: string
): Promise<{ results: SearchResult[] }> {
  const { data } = await api.get(`/content/${id}/recommendations`);
  return data;
}

// ─── Analytics ───────────────────────────────────────────────────

export interface KPIs {
  total_assets: number;
  total_searches: number;
  avg_hit_rate: number;
  top_category: string;
}

export async function getKPIs(): Promise<KPIs> {
  const { data } = await api.get("/analytics/kpis");
  return data;
}

export async function getTopContent(): Promise<SearchResult[]> {
  const { data } = await api.get("/analytics/top-content");
  return data;
}

export interface HitRatePoint {
  date: string;
  total_searches: number;
  zero_result_searches: number;
  hit_rate: number;
}

export async function getSearchHitRate(): Promise<HitRatePoint[]> {
  const { data } = await api.get("/analytics/search-hit-rate");
  return data;
}

export interface ZeroResultQuery {
  query: string;
  count: number;
  last_seen: string | null;
}

export async function getZeroResults(): Promise<ZeroResultQuery[]> {
  const { data } = await api.get("/analytics/zero-results");
  return data;
}

export interface GeoRegion {
  region: string;
  search_count: number;
  top_queries: string[];
}

export async function getGeoDistribution(): Promise<GeoRegion[]> {
  const { data } = await api.get("/analytics/geo-distribution");
  return data;
}

export interface EngagementCategory {
  category: string;
  trend: { date: string; views: number }[];
}

export async function getEngagementTrends(): Promise<EngagementCategory[]> {
  const { data } = await api.get("/analytics/engagement-trends");
  return data;
}

export interface ContentTypeBreakdown {
  content_type: string;
  count: number;
  total_views: number;
}

export async function getContentTypeBreakdown(): Promise<
  ContentTypeBreakdown[]
> {
  const { data } = await api.get("/analytics/content-type-breakdown");
  return data;
}

export async function logClick(contentId: string, queryText: string = "") {
  await api.post("/analytics/log-click", {
    content_id: contentId,
    query_text: queryText,
  });
}

// ─── Assets (GCS uploads) ───────────────────────────────────────

export interface AssetItem {
  id: string;
  title: string;
  description: string;
  content_type: string;
  tags: string[];
  category: string;
  source: string;
  url: string;
  thumbnail_url: string;
  file_type: string;
  created_at: string;
  width?: number;
  height?: number;
  gcs_bucket?: string;
  gcs_object?: string;
}

export interface AssetListResponse {
  total: number;
  assets: AssetItem[];
}

export interface UploadResponse {
  status: string;
  file: string;
  gcs_path: string;
  public_url: string;
  doc_id: string;
  message: string;
}

export async function uploadAsset(
  file: File,
  folder: string = "uploads"
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/assets/upload", form, {
    params: { folder },
    timeout: 120000,
  });
  return data;
}

export async function listAssets(
  size: number = 100
): Promise<AssetListResponse> {
  const { data } = await api.get("/assets", { params: { size } });
  return data;
}

export async function deleteAsset(docId: string): Promise<void> {
  await api.delete(`/assets/${docId}`);
}
