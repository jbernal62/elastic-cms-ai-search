import { useEffect, useState } from "react";
import { Database, Search, TrendingUp, Award } from "lucide-react";
import TopContentChart from "../components/charts/TopContentChart";
import SearchHitRateChart from "../components/charts/SearchHitRateChart";
import ZeroResultsTable from "../components/charts/ZeroResultsTable";
import GeoHeatmap from "../components/charts/GeoHeatmap";
import EngagementTrends from "../components/charts/EngagementTrends";
import ContentTypeChart from "../components/charts/ContentTypeChart";
import {
  getKPIs,
  getTopContent,
  getSearchHitRate,
  getZeroResults,
  getGeoDistribution,
  getEngagementTrends,
  getContentTypeBreakdown,
} from "../api/client";
import type {
  KPIs,
  SearchResult,
  HitRatePoint,
  ZeroResultQuery,
  GeoRegion,
  EngagementCategory,
  ContentTypeBreakdown,
} from "../api/client";

interface KPICardProps {
  label: string;
  value: string | number;
  icon: typeof Database;
  color: string;
}

function KPICard({ label, value, icon: Icon, color }: KPICardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900">
            {typeof value === "number" ? value.toLocaleString() : value}
          </p>
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [topContent, setTopContent] = useState<SearchResult[]>([]);
  const [hitRate, setHitRate] = useState<HitRatePoint[]>([]);
  const [zeroResults, setZeroResults] = useState<ZeroResultQuery[]>([]);
  const [geo, setGeo] = useState<GeoRegion[]>([]);
  const [engagement, setEngagement] = useState<EngagementCategory[]>([]);
  const [contentTypes, setContentTypes] = useState<ContentTypeBreakdown[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getKPIs(),
      getTopContent(),
      getSearchHitRate(),
      getZeroResults(),
      getGeoDistribution(),
      getEngagementTrends(),
      getContentTypeBreakdown(),
    ])
      .then(
        ([
          kpisData,
          topData,
          hitRateData,
          zeroData,
          geoData,
          engData,
          typeData,
        ]) => {
          setKpis(kpisData);
          setTopContent(topData);
          setHitRate(hitRateData);
          setZeroResults(zeroData);
          setGeo(geoData);
          setEngagement(engData);
          setContentTypes(typeData);
        }
      )
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="text-center py-20 text-gray-400">
        Loading dashboard...
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Content Analytics Dashboard
        </h1>
        <p className="text-gray-500">
          Observability insights for CMS content discovery, search performance,
          and user engagement patterns.
        </p>
      </div>

      {/* KPI cards */}
      {kpis && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <KPICard
            label="Total Assets"
            value={kpis.total_assets}
            icon={Database}
            color="bg-indigo-500"
          />
          <KPICard
            label="Total Searches"
            value={kpis.total_searches}
            icon={Search}
            color="bg-purple-500"
          />
          <KPICard
            label="Avg Hit Rate"
            value={`${kpis.avg_hit_rate}%`}
            icon={TrendingUp}
            color="bg-green-500"
          />
          <KPICard
            label="Top Category"
            value={kpis.top_category}
            icon={Award}
            color="bg-orange-500"
          />
        </div>
      )}

      {/* Charts grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TopContentChart data={topContent} />
        <SearchHitRateChart data={hitRate} />
        <ZeroResultsTable data={zeroResults} />
        <GeoHeatmap data={geo} />
        <EngagementTrends data={engagement} />
        <ContentTypeChart data={contentTypes} />
      </div>
    </div>
  );
}
