import { useQuery } from '@tanstack/react-query';
import { Clock, Target, TrendingUp, Activity, ShieldAlert } from 'lucide-react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
} from 'recharts';
import api from '../../lib/api-client';
import type { AnalyticsSummary, DateCount, SeverityCount, TypeCount, ViolationListResponse } from '../../types';

const SEVERITY_COLORS: Record<string, string> = {
  low: '#10b981',
  medium: '#f59e0b',
  high: '#ef4444',
  critical: '#dc2626',
};

const BAR_COLORS = ['#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#f97316', '#6366f1', '#ef4444'];

export default function DashboardPage() {
  const { data: summary } = useQuery<AnalyticsSummary>({
    queryKey: ['summary'],
    queryFn: () => api.get('/analytics/summary').then((r) => r.data),
  });
  const { data: byType } = useQuery<TypeCount[]>({
    queryKey: ['by-type'],
    queryFn: () => api.get('/analytics/by-type').then((r) => r.data),
  });
  const { data: trends } = useQuery<DateCount[]>({
    queryKey: ['trends'],
    queryFn: () => api.get('/analytics/trends?days=14').then((r) => r.data),
  });
  const { data: bySeverity } = useQuery<SeverityCount[]>({
    queryKey: ['by-severity'],
    queryFn: () => api.get('/analytics/by-severity').then((r) => r.data),
  });
  const { data: recentViolations } = useQuery<ViolationListResponse>({
    queryKey: ['recent-violations'],
    queryFn: () => api.get('/violations?page=1&limit=5').then((r) => r.data),
  });

  const stats = [
    {
      label: 'Total Violations',
      value: summary?.total_violations ?? 0,
      icon: ShieldAlert,
      gradient: 'from-red-500 to-rose-600',
      bg: 'bg-red-500/5',
      border: 'border-l-red-500',
      delta: '+12%',
      deltaUp: true,
    },
    {
      label: "Today's Count",
      value: summary?.today_violations ?? 0,
      icon: TrendingUp,
      gradient: 'from-cyan-400 to-blue-500',
      bg: 'bg-cyan-500/5',
      border: 'border-l-cyan-400',
      delta: '+3',
      deltaUp: true,
    },
    {
      label: 'Avg Confidence',
      value: `${Math.round((summary?.avg_confidence ?? 0) * 100)}%`,
      icon: Target,
      gradient: 'from-emerald-400 to-green-500',
      bg: 'bg-emerald-500/5',
      border: 'border-l-emerald-400',
      delta: '+2.1%',
      deltaUp: true,
    },
    {
      label: 'Pending Review',
      value: summary?.pending_review ?? 0,
      icon: Clock,
      gradient: 'from-orange-400 to-amber-500',
      bg: 'bg-orange-500/5',
      border: 'border-l-orange-400',
      delta: '-5',
      deltaUp: false,
    },
  ];

  const maxTypeCount = Math.max(...(byType ?? []).map((t) => t.count), 1);

  const pieData = (bySeverity ?? []).map((s) => ({
    ...s,
    fill: SEVERITY_COLORS[s.severity.toLowerCase()] ?? '#6366f1',
  }));

  return (
    <div className="min-h-screen bg-[#0a0a0f] p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Activity className="w-7 h-7 text-cyan-400" />
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Command Center</h2>
          <p className="text-xs text-gray-500 tracking-wide">Real-time traffic violation monitoring</p>
        </div>
      </div>

      {/* Hero Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => (
          <div
            key={s.label}
            className={`relative overflow-hidden rounded-xl border border-[#1e1e2e] ${s.bg} backdrop-blur-sm border-l-4 ${s.border} p-5 group hover:border-[#2a2a3e] transition-all duration-300`}
            style={{ background: 'rgba(18,18,26,0.8)' }}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium tracking-wider uppercase text-gray-500">{s.label}</span>
              <div className={`p-2 rounded-lg bg-gradient-to-br ${s.gradient} bg-opacity-20`}>
                <s.icon className="w-4 h-4 text-white" />
              </div>
            </div>
            <p className="text-3xl font-bold text-white tracking-tight">{s.value}</p>
            <div className="mt-2 flex items-center gap-1">
              <span className={`text-xs font-medium ${s.deltaUp ? 'text-emerald-400' : 'text-red-400'}`}>
                {s.delta}
              </span>
              <span className="text-xs text-gray-600">vs last week</span>
            </div>
            {/* Subtle gradient glow */}
            <div className={`absolute -top-12 -right-12 w-24 h-24 rounded-full bg-gradient-to-br ${s.gradient} opacity-5 blur-2xl group-hover:opacity-10 transition-opacity`} />
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Violations by Type - Horizontal Bar */}
        <div className="rounded-xl border border-[#1e1e2e] p-5" style={{ background: 'rgba(18,18,26,0.8)' }}>
          <h3 className="font-semibold text-sm tracking-wide text-gray-300 mb-5">Violations by Type</h3>
          <div className="space-y-3">
            {(byType ?? []).map((t, i) => {
              const pct = (t.count / maxTypeCount) * 100;
              return (
                <div key={t.type} className="group">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-400 capitalize tracking-wide">{t.type.replace(/_/g, ' ')}</span>
                    <span className="text-xs font-mono text-gray-500">{t.count}</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-[#1a1a2e] overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700 ease-out"
                      style={{
                        width: `${pct}%`,
                        background: `linear-gradient(90deg, ${BAR_COLORS[i % BAR_COLORS.length]}, ${BAR_COLORS[i % BAR_COLORS.length]}aa)`,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Severity Distribution - Donut */}
        <div className="rounded-xl border border-[#1e1e2e] p-5" style={{ background: 'rgba(18,18,26,0.8)' }}>
          <h3 className="font-semibold text-sm tracking-wide text-gray-300 mb-4">Severity Distribution</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={pieData}
                dataKey="count"
                nameKey="severity"
                cx="50%"
                cy="50%"
                innerRadius={65}
                outerRadius={100}
                strokeWidth={2}
                stroke="#0a0a0f"
              >
                {pieData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: '#12121a',
                  border: '1px solid #1e1e2e',
                  borderRadius: 10,
                  fontSize: 12,
                  boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
                }}
                itemStyle={{ color: '#e5e7eb' }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-4 -mt-2">
            {pieData.map((s) => (
              <div key={s.severity} className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: s.fill }} />
                <span className="text-xs text-gray-500 capitalize">{s.severity}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Daily Trends - Area Chart */}
        <div className="rounded-xl border border-[#1e1e2e] p-5 lg:col-span-2" style={{ background: 'rgba(18,18,26,0.8)' }}>
          <h3 className="font-semibold text-sm tracking-wide text-gray-300 mb-4">Daily Trends (Last 14 Days)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={[...(trends ?? [])].reverse()}>
              <defs>
                <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: '#4b5563', fontSize: 11 }} axisLine={{ stroke: '#1e1e2e' }} tickLine={false} />
              <YAxis tick={{ fill: '#4b5563', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{
                  background: '#12121a',
                  border: '1px solid #1e1e2e',
                  borderRadius: 10,
                  fontSize: 12,
                  boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
                }}
                itemStyle={{ color: '#e5e7eb' }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#06b6d4"
                strokeWidth={2}
                fill="url(#trendGrad)"
                dot={{ fill: '#06b6d4', r: 3, strokeWidth: 0 }}
                activeDot={{ r: 5, fill: '#06b6d4', stroke: '#0a0a0f', strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Violations Table */}
      <div className="rounded-xl border border-[#1e1e2e] overflow-hidden" style={{ background: 'rgba(18,18,26,0.8)' }}>
        <div className="px-5 py-4 border-b border-[#1e1e2e]">
          <h3 className="font-semibold text-sm tracking-wide text-gray-300">Recent Violations</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 uppercase tracking-wider border-b border-[#1e1e2e]">
                <th className="text-left px-5 py-3 font-medium">Type</th>
                <th className="text-left px-5 py-3 font-medium">Severity</th>
                <th className="text-left px-5 py-3 font-medium">Confidence</th>
                <th className="text-left px-5 py-3 font-medium">Plate</th>
                <th className="text-left px-5 py-3 font-medium">Status</th>
                <th className="text-left px-5 py-3 font-medium">Time</th>
              </tr>
            </thead>
            <tbody>
              {(recentViolations?.items ?? []).map((v) => (
                <tr key={v.id} className="border-b border-[#1e1e2e]/50 hover:bg-white/[0.02] transition-colors">
                  <td className="px-5 py-3 text-gray-300 capitalize font-medium">{v.violation_type.replace(/_/g, ' ')}</td>
                  <td className="px-5 py-3">
                    <span
                      className="px-2 py-0.5 rounded-full text-xs font-medium capitalize"
                      style={{
                        background: `${SEVERITY_COLORS[v.severity.toLowerCase()] ?? '#6366f1'}20`,
                        color: SEVERITY_COLORS[v.severity.toLowerCase()] ?? '#6366f1',
                      }}
                    >
                      {v.severity}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 rounded-full bg-[#1a1a2e] overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${v.confidence * 100}%`,
                            background: v.confidence >= 0.8 ? '#10b981' : v.confidence >= 0.5 ? '#f59e0b' : '#ef4444',
                          }}
                        />
                      </div>
                      <span className="text-xs font-mono text-gray-400">{(v.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className="px-5 py-3 text-gray-400 font-mono text-xs">{v.plate_number ?? '--'}</td>
                  <td className="px-5 py-3">
                    <span className={`text-xs font-medium ${v.status === 'confirmed' ? 'text-emerald-400' : v.status === 'pending' ? 'text-amber-400' : 'text-gray-500'}`}>
                      {v.status}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-gray-500 text-xs">
                    {v.detected_at ? new Date(v.detected_at).toLocaleString() : '--'}
                  </td>
                </tr>
              ))}
              {(!recentViolations?.items || recentViolations.items.length === 0) && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-gray-600">No violations recorded yet</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
