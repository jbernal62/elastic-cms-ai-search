import { Routes, Route, NavLink } from "react-router-dom";
import { Search, ImageIcon, FileText, BarChart3, FolderUp } from "lucide-react";
import SearchPage from "./pages/SearchPage";
import ImageSearchPage from "./pages/ImageSearchPage";
import ComparisonPage from "./pages/ComparisonPage";
import ContentDetailPage from "./pages/ContentDetailPage";
import DashboardPage from "./pages/DashboardPage";
import AssetsPage from "./pages/AssetsPage";

const navItems = [
  { to: "/", icon: Search, label: "Search" },
  { to: "/image-search", icon: ImageIcon, label: "Image Search" },
  { to: "/assets", icon: FolderUp, label: "Assets" },
  { to: "/dashboard", icon: BarChart3, label: "Dashboard" },
];

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top navbar */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <NavLink to="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
                <Search className="w-5 h-5 text-white" />
              </div>
              <span className="text-lg font-bold text-gray-900">
                CMS AI Search
              </span>
            </NavLink>

            {/* Nav links */}
            <div className="flex items-center gap-1">
              {navItems.map(({ to, icon: Icon, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-indigo-50 text-indigo-700"
                        : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </NavLink>
              ))}
            </div>
          </div>
        </div>
      </nav>

      {/* Page content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/image-search" element={<ImageSearchPage />} />
          <Route path="/compare" element={<ComparisonPage />} />
          <Route path="/content/:id" element={<ContentDetailPage />} />
          <Route path="/assets" element={<AssetsPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </main>
    </div>
  );
}
