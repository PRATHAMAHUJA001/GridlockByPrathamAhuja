import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  ScanSearch,
  AlertTriangle,
  BarChart3,
  Settings,
  Brain,
  Shield,
  Search,
  Circle,
} from 'lucide-react';

const NAV_ITEMS = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/detect', label: 'Live Detection', icon: ScanSearch },
  { path: '/ai-analysis', label: 'AI Analysis', icon: Brain },
  { path: '/violations', label: 'Violation Records', icon: AlertTriangle },
  { path: '/analytics', label: 'AI Analytics', icon: BarChart3 },
  { path: '/settings', label: 'System Settings', icon: Settings },
];

export default function Layout() {
  const location = useLocation();

  return (
    <div className="flex h-screen bg-[#0a0a0f] text-gray-100">
      {/* Sidebar */}
      <aside className="w-64 border-r border-[#1e1e2e] flex flex-col bg-[#0c0c14]">
        <div className="p-5 border-b border-[#1e1e2e]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-base tracking-tight">TrafficSarathi</h1>
              <p className="text-[10px] tracking-[0.2em] text-gray-500 uppercase">Command Center v4.2</p>
            </div>
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-0.5">
          {NAV_ITEMS.map(({ path, label, icon: Icon }) => {
            const active = location.pathname === path;
            return (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all relative ${
                  active
                    ? 'bg-cyan-500/10 text-cyan-400'
                    : 'text-gray-500 hover:bg-white/5 hover:text-gray-300'
                }`}
              >
                {active && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-gradient-to-b from-cyan-400 to-blue-500" />
                )}
                <Icon className="w-[18px] h-[18px]" />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-[#1e1e2e]">
          <Link
            to="/"
            className="text-xs text-gray-600 hover:text-gray-400 transition-colors"
          >
            TrafficSarathi v1.0 — View Landing Page
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Status Bar */}
        <header className="h-12 border-b border-[#1e1e2e] bg-[#0c0c14] flex items-center justify-between px-5 shrink-0">
          <div className="flex items-center gap-2 text-sm">
            <Search className="w-4 h-4 text-gray-600" />
            <input
              type="text"
              placeholder="Global system search..."
              className="bg-transparent border-none outline-none text-gray-400 placeholder-gray-600 text-sm w-64"
            />
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs">
              <Circle className="w-2 h-2 fill-emerald-400 text-emerald-400" />
              <span className="text-emerald-400 font-medium">Online</span>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
