import { useQuery } from '@tanstack/react-query';
import { Brain, BarChart3, PieChart as PieIcon, TrendingUp, Layers } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, PieChart, Pie, Cell, Legend,
} from 'recharts';
import api from '../../lib/api-client';
import type { AnalyticsSummary, TypeCount, DateCount, SeverityCount } from '../../types';

const COLORS = ['#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#f97316'];
const SEVERITY_COLORS: Record<string, string> = { low: '#10b981', medium: '#f59e0b', high: '#ef4444', critical: '#dc2626' };

const tooltipStyle = {
  background: '#12121a',
  border: '1px solid #1e1e2e',
  borderRadius: 10,
  fontSize: 12,
  boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
};

export default function AnalyticsPage() {
  const { data: summary } = useQuery<AnalyticsSummary>({
    queryKey: ['summary'],
    queryFn: () => api.get('/analytics/summary').then((r) => r.data),
  });
  const { data: byType } = useQuery<TypeCount[]>({
    queryKey: ['analytics-type'],
    queryFn: () => api.get('/analytics/by-type').then((r) => r.data),
  });
  const { data: trends } = useQuery<DateCount[]>({
    queryKey: ['analytics-trends'],
    queryFn: () => api.get('/analytics/trends?days=30').then((r) => r.data),
  });
  const { data: bySeverity } = useQuery<SeverityCount[]>({
    queryKey: ['analytics-severity'],
    queryFn: () => api.get('/analytics/by-severity').then((r) => r.data),
  });

  const totalViolations = (byType ?? []).reduce((sum, t) => sum + t.count, 0);
  const avgConfidence = (byType ?? []).length > 0
    ? (byType ?? []).reduce((sum, t) => sum + t.avg_confidence * t.count, 0) / totalViolations
    : 0;
  const topType = (byType ?? []).reduce((max, t) => (t.count > (max?.count ?? 0) ? t : max), byType?.[0]);

  const summaryStats = [
    { label: 'Total Detected', value: summary?.total_violations ?? totalViolations, icon: Layers, color: 'from-cyan-400 to-blue-500' },
    { label: 'Violation Types', value: (byType ?? []).length, icon: BarChart3, color: 'from-purple-400 to-violet-500' },
    { label: 'Avg Confidence', value: `${Math.round((summary?.avg_confidence ?? avgConfidence) * 100)}%`, icon: TrendingUp, color: 'from-emerald-400 to-green-500' },
    { label: 'Top Violation', value: topType?.type?.replace(/_/g, ' ') ?? '--', icon: PieIcon, color: 'from-orange-400 to-amber-500', capitalize: true },
  ];

  const pieData = (bySeverity ?? []).map((s) => ({
    ...s,
    fill: SEVERITY_COLORS[s.severity.toLowerCase()] ?? '#6366f1',
  }));

  return (
    <div className="min-h-screen bg-[#0a0a0f] p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500 to-blue-600">
          <Brain className="w-5 h-5 text-white" />
        </div>
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">AI Analytics</h2>
          <p className="text-xs text-gray-500 tracking-wide">Deep insights into traffic violation patterns</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryStats.map((s) => (
          <div
            key={s.label}
            className="rounded-xl border border-[#1e1e2e] p-5 hover:border-[#2a2a3e] transition-all duration-300"
            style={{ background: 'rgba(18,18,26,0.8)' }}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium tracking-wider uppercase text-gray-500">{s.label}</span>
              <div className={`p-2 rounded-lg bg-gradient-to-br ${s.color}`}>
                <s.icon className="w-4 h-4 text-white" />
              </div>
            </div>
            <p className={`text-2xl font-bold text-white tracking-tight ${s.capitalize ? 'capitalize text-lg' : ''}`}>{s.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 30-Day Trend - Area */}
        <div className="rounded-xl border border-[#1e1e2e] p-5 lg:col-span-2" style={{ background: 'rgba(18,18,26,0.8)' }}>
          <h3 className="font-semibold text-sm tracking-wide text-gray-300 mb-4">30-Day Trend</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={[...(trends ?? [])].reverse()}>
              <defs>
                <linearGradient id="analyticsTrendGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: '#4b5563', fontSize: 11 }} axisLine={{ stroke: '#1e1e2e' }} tickLine={false} />
              <YAxis tick={{ fill: '#4b5563', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: '#e5e7eb' }} />
              <Area type="monotone" dataKey="count" stroke="#8b5cf6" strokeWidth={2} fill="url(#analyticsTrendGrad)" dot={{ fill: '#8b5cf6', r: 3, strokeWidth: 0 }} activeDot={{ r: 5, fill: '#8b5cf6', stroke: '#0a0a0f', strokeWidth: 2 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Violations by Type - Stacked/Colored Bar */}
        <div className="rounded-xl border border-[#1e1e2e] p-5" style={{ background: 'rgba(18,18,26,0.8)' }}>
          <h3 className="font-semibold text-sm tracking-wide text-gray-300 mb-4">Violations by Type</h3>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={byType ?? []} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#4b5563', fontSize: 11 }} axisLine={{ stroke: '#1e1e2e' }} tickLine={false} />
              <YAxis dataKey="type" type="category" tick={{ fill: '#9ca3af', fontSize: 11 }} width={100} axisLine={false} tickLine={false} tickFormatter={(v: string) => v.replace(/_/g, ' ')} />
              <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: '#e5e7eb' }} />
              <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                {(byType ?? []).map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Severity Breakdown - Donut */}
        <div className="rounded-xl border border-[#1e1e2e] p-5" style={{ background: 'rgba(18,18,26,0.8)' }}>
          <h3 className="font-semibold text-sm tracking-wide text-gray-300 mb-4">Severity Breakdown</h3>
          <ResponsiveContainer width="100%" height={350}>
            <PieChart>
              <Pie data={pieData} dataKey="count" nameKey="severity" cx="50%" cy="50%" innerRadius={70} outerRadius={110} strokeWidth={2} stroke="#0a0a0f">
                {pieData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: '#e5e7eb' }} />
              <Legend formatter={(value: string) => <span className="text-xs text-gray-400 capitalize">{value}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Confidence by Violation Type */}
        {byType && byType.length > 0 && (
          <div className="rounded-xl border border-[#1e1e2e] p-5 lg:col-span-2" style={{ background: 'rgba(18,18,26,0.8)' }}>
            <h3 className="font-semibold text-sm tracking-wide text-gray-300 mb-4">Confidence Distribution</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {byType.map((t) => {
                const conf = Math.round(t.avg_confidence * 100);
                const confColor = conf >= 80 ? '#10b981' : conf >= 50 ? '#f59e0b' : '#ef4444';
                return (
                  <div
                    key={t.type}
                    className="rounded-xl border border-[#1e1e2e] p-4 text-center hover:border-[#2a2a3e] transition-all"
                    style={{ background: 'rgba(26,26,46,0.5)' }}
                  >
                    <p className="text-xs text-gray-500 capitalize tracking-wide mb-2">{t.type.replace(/_/g, ' ')}</p>
                    <p className="text-3xl font-bold" style={{ color: confColor }}>{conf}%</p>
                    <div className="mt-2 w-full h-1 rounded-full bg-[#1a1a2e] overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${conf}%`, background: confColor }} />
                    </div>
                    <p className="text-xs text-gray-600 mt-2">{t.count} violations</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
