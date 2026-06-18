import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Trash2, Database, AlertTriangle, Loader2, CheckCircle2, Server, Cpu, Shield, Activity } from 'lucide-react';
import api from '../../lib/api-client';

interface DbStats {
  violations: number;
  vehicles: number;
  images: number;
  users: number;
  snapshots: number;
}

const STAT_ITEMS = [
  { key: 'violations' as const, label: 'Violations', color: '#ef4444', bg: 'rgba(239,68,68,0.08)' },
  { key: 'vehicles' as const, label: 'Vehicles', color: '#f59e0b', bg: 'rgba(245,158,11,0.08)' },
  { key: 'images' as const, label: 'Images', color: '#3b82f6', bg: 'rgba(59,130,246,0.08)' },
  { key: 'users' as const, label: 'Users', color: '#10b981', bg: 'rgba(16,185,129,0.08)' },
  { key: 'snapshots' as const, label: 'Snapshots', color: '#8b5cf6', bg: 'rgba(139,92,246,0.08)' },
];

const TECH_STACK = [
  { label: 'FastAPI', color: '#10b981' },
  { label: 'SQLAlchemy', color: '#3b82f6' },
  { label: 'SQLite', color: '#f59e0b' },
  { label: 'YOLOv8', color: '#ef4444' },
  { label: 'OpenCV', color: '#06b6d4' },
  { label: 'EasyOCR', color: '#8b5cf6' },
  { label: 'React', color: '#06b6d4' },
  { label: 'TypeScript', color: '#3b82f6' },
  { label: 'Tailwind CSS', color: '#06b6d4' },
  { label: 'TanStack Query', color: '#f97316' },
];

export default function SettingsPage() {
  const [showConfirm, setShowConfirm] = useState(false);
  const queryClient = useQueryClient();

  const { data: stats, isLoading: statsLoading } = useQuery<DbStats>({
    queryKey: ['db-stats'],
    queryFn: () => api.get('/admin/db-stats').then((r) => r.data),
    refetchInterval: 5000,
  });

  const cleanMutation = useMutation({
    mutationFn: () => api.delete('/admin/clean-db').then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries();
      setShowConfirm(false);
    },
  });

  const totalRecords = stats
    ? stats.violations + stats.vehicles + stats.images + stats.snapshots
    : 0;

  return (
    <div className="min-h-screen bg-[#0a0a0f] p-6 space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-gradient-to-br from-gray-500 to-gray-700">
          <Server className="w-5 h-5 text-white" />
        </div>
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">System Settings</h2>
          <p className="text-xs text-gray-500 tracking-wide">Database management and system configuration</p>
        </div>
      </div>

      {/* System Health */}
      <div className="rounded-xl border border-[#1e1e2e] p-5" style={{ background: 'rgba(18,18,26,0.8)' }}>
        <div className="flex items-center gap-3 mb-5">
          <Activity className="w-5 h-5 text-emerald-400" />
          <h3 className="font-semibold text-sm tracking-wide text-gray-300">System Health</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { label: 'API Server', status: 'Operational', color: '#10b981' },
            { label: 'ML Pipeline', status: 'Operational', color: '#10b981' },
            { label: 'Database', status: 'Operational', color: '#10b981' },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-3 rounded-lg border border-[#1e1e2e] p-3" style={{ background: 'rgba(26,26,46,0.5)' }}>
              <div className="relative">
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: item.color }} />
                <div className="absolute inset-0 w-2.5 h-2.5 rounded-full animate-ping opacity-30" style={{ background: item.color }} />
              </div>
              <div>
                <p className="text-sm text-gray-300 font-medium">{item.label}</p>
                <p className="text-xs" style={{ color: item.color }}>{item.status}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Database Stats */}
      <div className="rounded-xl border border-[#1e1e2e] p-6" style={{ background: 'rgba(18,18,26,0.8)' }}>
        <div className="flex items-center gap-3 mb-5">
          <Database className="w-5 h-5 text-blue-400" />
          <h3 className="font-semibold text-sm tracking-wide text-gray-300">Database (SQLite)</h3>
        </div>

        {statsLoading ? (
          <div className="flex items-center gap-2 text-gray-400">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading stats...
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
            {STAT_ITEMS.map((item) => (
              <div
                key={item.key}
                className="rounded-xl border border-[#1e1e2e] p-4 text-center hover:border-[#2a2a3e] transition-all"
                style={{ background: item.bg }}
              >
                <p className="text-2xl font-bold" style={{ color: item.color }}>{stats?.[item.key] ?? 0}</p>
                <p className="text-xs text-gray-500 mt-1 tracking-wide">{item.label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Danger Zone */}
        <div className="rounded-xl border border-red-900/30 p-5 mt-2" style={{ background: 'rgba(127,29,29,0.08)', borderImage: 'linear-gradient(135deg, #dc2626, #991b1b) 1' }}>
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5 shrink-0" />
            <div className="flex-1">
              <h4 className="font-medium text-red-400 text-sm tracking-wide">Danger Zone</h4>
              <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                Clean the database to remove all violations, vehicles, images, and analytics data.
                Uploaded and evidence images will also be deleted. This action cannot be undone.
              </p>

              {!showConfirm ? (
                <button
                  onClick={() => setShowConfirm(true)}
                  disabled={totalRecords === 0}
                  className="mt-4 flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed border border-red-800/50 text-red-300 hover:bg-red-900/30"
                  style={{ background: 'rgba(127,29,29,0.2)' }}
                >
                  <Trash2 className="w-4 h-4" />
                  Clean Database ({totalRecords} records)
                </button>
              ) : (
                <div className="mt-4 rounded-xl border border-red-800/50 p-4 space-y-3" style={{ background: 'rgba(127,29,29,0.15)' }}>
                  <p className="text-sm text-red-300 font-medium">
                    Are you sure? This will permanently delete all {totalRecords} records.
                  </p>
                  <div className="flex gap-3">
                    <button
                      onClick={() => cleanMutation.mutate()}
                      disabled={cleanMutation.isPending}
                      className="flex items-center gap-2 px-4 py-2.5 bg-red-600 hover:bg-red-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                    >
                      {cleanMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                      Yes, Delete Everything
                    </button>
                    <button
                      onClick={() => setShowConfirm(false)}
                      className="px-4 py-2.5 rounded-lg text-sm font-medium text-gray-400 border border-[#1e1e2e] hover:border-[#2a2a3e] transition-colors"
                      style={{ background: 'rgba(18,18,26,0.8)' }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {cleanMutation.isSuccess && (
                <div className="mt-3 flex items-center gap-2 text-emerald-400 text-sm">
                  <CheckCircle2 className="w-4 h-4" />
                  Database cleaned successfully
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* System Info */}
      <div className="rounded-xl border border-[#1e1e2e] p-6" style={{ background: 'rgba(18,18,26,0.8)' }}>
        <div className="flex items-center gap-3 mb-5">
          <Cpu className="w-5 h-5 text-purple-400" />
          <h3 className="font-semibold text-sm tracking-wide text-gray-300">System Information</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-orange-400" />
            <span className="text-sm text-gray-300 font-medium">TrafficSarathi v1.0</span>
            <span className="text-xs bg-orange-500/10 text-orange-400 px-2 py-0.5 rounded-full font-medium">Production</span>
          </div>

          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Tech Stack</p>
            <div className="flex flex-wrap gap-2">
              {TECH_STACK.map((tech) => (
                <span
                  key={tech.label}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium border border-[#1e1e2e] hover:border-[#2a2a3e] transition-colors"
                  style={{ background: `${tech.color}10`, color: tech.color }}
                >
                  {tech.label}
                </span>
              ))}
            </div>
          </div>

          <div className="pt-2">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Architecture</p>
            <p className="text-sm text-gray-400">N-Layered: Presentation &gt; Service &gt; Domain &gt; Data Access &gt; Infrastructure</p>
          </div>
        </div>
      </div>
    </div>
  );
}
