import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Search,
  Filter,
  X,
  Eye,
  CheckCircle2,
  XCircle,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  Loader2,
  Image as ImageIcon,
} from 'lucide-react';
import api from '../../lib/api-client';
import type { ViolationListResponse } from '../../types';
import ConfidenceBadge from '../../components/ConfidenceBadge';
import SeverityBadge from '../../components/SeverityBadge';

interface ViolationDetail {
  id: string;
  violation_type: string;
  severity: string;
  confidence: number;
  detected_at: string | null;
  status: string;
  location: string | null;
  plate_number: string | null;
  bbox_x: number;
  bbox_y: number;
  bbox_w: number;
  bbox_h: number;
  vehicle_category: string | null;
  original_image_url: string | null;
  evidence_image_url: string | null;
  all_violation_types: string[];
}

const TYPES = ['helmet', 'seatbelt', 'triple_riding', 'wrong_side', 'stop_line', 'red_light', 'illegal_parking'];

export default function ViolationsPage() {
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [plateSearch, setPlateSearch] = useState('');
  const [reviewId, setReviewId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<ViolationListResponse>({
    queryKey: ['violations', page, typeFilter, severityFilter],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), limit: '15' });
      if (typeFilter) params.set('violation_type', typeFilter);
      if (severityFilter) params.set('severity', severityFilter);
      return api.get(`/violations?${params}`).then((r) => r.data);
    },
  });

  const { data: detail, isLoading: detailLoading } = useQuery<ViolationDetail>({
    queryKey: ['violation-detail', reviewId],
    queryFn: () => api.get(`/violations/${reviewId}`).then((r) => r.data),
    enabled: !!reviewId,
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.patch(`/violations/${id}`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['violations'] });
      queryClient.invalidateQueries({ queryKey: ['violation-detail'] });
    },
  });

  const openReview = (id: string) => {
    setReviewId(id);
  };

  const totalPages = data ? Math.ceil(data.total / 15) : 0;

  const filteredItems = data?.items.filter(
    (v) => !plateSearch || (v.plate_number ?? '').toLowerCase().includes(plateSearch.toLowerCase())
  );

  return (
    <div className="p-6 space-y-5 relative">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Detection Logs — Last 24 Hours</h2>
        </div>
        {data && (
          <span className="text-xs font-mono text-cyan-400 tracking-wider">
            {data.total} RECORDS FOUND
          </span>
        )}
      </div>

      {/* Filter Bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2 bg-[#12121a] border border-[#1e1e2e] rounded-lg px-3 py-2 flex-1 max-w-xs">
          <Search className="w-4 h-4 text-gray-600" />
          <input
            type="text"
            placeholder="License Plate OCR"
            value={plateSearch}
            onChange={(e) => setPlateSearch(e.target.value)}
            className="bg-transparent border-none outline-none text-sm text-gray-300 placeholder-gray-600 flex-1"
          />
        </div>
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
          className="bg-[#12121a] border border-[#1e1e2e] rounded-lg px-3 py-2 text-sm text-gray-300 outline-none"
        >
          <option value="">Violation Type: All</option>
          {TYPES.map((t) => (
            <option key={t} value={t} className="capitalize">{t.replace(/_/g, ' ')}</option>
          ))}
        </select>
        <select
          value={severityFilter}
          onChange={(e) => { setSeverityFilter(e.target.value); setPage(1); }}
          className="bg-[#12121a] border border-[#1e1e2e] rounded-lg px-3 py-2 text-sm text-gray-300 outline-none"
        >
          <option value="">Severity: All</option>
          {['low', 'medium', 'high', 'critical'].map((s) => (
            <option key={s} value={s} className="capitalize">{s}</option>
          ))}
        </select>
        <button className="flex items-center gap-2 bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-sm font-medium px-4 py-2 rounded-lg hover:bg-cyan-500/20 transition-colors">
          <Filter className="w-3.5 h-3.5" />
          Apply Filters
        </button>
      </div>

      {/* Table */}
      <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#1e1e2e] text-gray-500 text-left text-xs uppercase tracking-wider">
              <th className="px-4 py-3 font-medium">Violation</th>
              <th className="px-4 py-3 font-medium">Plate OCR</th>
              <th className="px-4 py-3 font-medium">Timestamp</th>
              <th className="px-4 py-3 font-medium">Confidence</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={6} className="text-center py-16 text-gray-600">
                  <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" />
                  Loading...
                </td>
              </tr>
            )}
            {filteredItems?.map((v) => (
              <tr
                key={v.id}
                className="border-b border-[#1e1e2e]/50 hover:bg-white/[0.02] transition-colors cursor-pointer"
                onClick={() => openReview(v.id)}
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <SeverityBadge severity={v.severity} />
                    <span className="font-medium capitalize text-gray-200">
                      {v.violation_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="font-mono text-sm text-gray-300">
                    {v.plate_number ?? '—'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {v.detected_at ? new Date(v.detected_at).toLocaleString() : '—'}
                </td>
                <td className="px-4 py-3">
                  <ConfidenceBadge value={v.confidence} />
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`text-[10px] font-bold tracking-wider px-2.5 py-1 rounded border uppercase ${
                      v.status === 'confirmed'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : v.status === 'dismissed'
                          ? 'bg-gray-500/10 text-gray-400 border-gray-500/20'
                          : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}
                  >
                    {v.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={(e) => { e.stopPropagation(); openReview(v.id); }}
                    className="text-xs font-medium text-cyan-400 hover:text-cyan-300 transition-colors flex items-center gap-1 ml-auto"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    Review
                  </button>
                </td>
              </tr>
            ))}
            {data && data.items.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-16 text-gray-600">
                  No violations found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-3">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-2 bg-[#12121a] border border-[#1e1e2e] rounded-lg disabled:opacity-30 hover:border-[#2e2e3e] transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs text-gray-500 font-mono">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= totalPages}
            className="p-2 bg-[#12121a] border border-[#1e1e2e] rounded-lg disabled:opacity-30 hover:border-[#2e2e3e] transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Review Modal */}
      {reviewId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-[#12121a] border border-[#1e1e2e] rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-auto mx-4 shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-5 border-b border-[#1e1e2e]">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-orange-400" />
                <h3 className="font-bold text-lg">Violation Review</h3>
              </div>
              <button
                onClick={() => setReviewId(null)}
                className="p-1.5 hover:bg-white/5 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            {detailLoading ? (
              <div className="p-12 text-center text-gray-500">
                <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                Loading violation details...
              </div>
            ) : detail ? (
              <div className="p-5 space-y-5">
                {/* Evidence Images */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-wider">
                      <ImageIcon className="w-3.5 h-3.5 text-orange-400" />
                      <span className="text-orange-400">Violation Crop</span>
                    </div>
                    <img
                      src={`/api/v1/violations/${detail.id}/crop`}
                      alt="Violation region"
                      className="rounded-xl border border-orange-500/30 w-full bg-[#0a0a0f]"
                    />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-wider">
                      <Eye className="w-3.5 h-3.5 text-cyan-400" />
                      <span className="text-cyan-400">AI Annotated Evidence</span>
                    </div>
                    {detail.evidence_image_url ? (
                      <div className="relative">
                        <img
                          src={detail.evidence_image_url}
                          alt="Evidence"
                          className="rounded-xl border border-[#1e1e2e] w-full"
                        />
                        <div className="absolute top-3 left-3 flex flex-col gap-1.5">
                          <span className="bg-red-500 text-white text-[10px] font-bold px-2 py-0.5 rounded tracking-wider">
                            VIOLATION DETECTED
                          </span>
                          {detail.plate_number && (
                            <span className="bg-emerald-500 text-white text-[10px] font-bold px-2 py-0.5 rounded tracking-wider">
                              PLATE CONFIRMED
                            </span>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="bg-[#0a0a0f] rounded-xl border border-[#1e1e2e] h-48 flex items-center justify-center text-gray-600 text-sm">
                        No evidence
                      </div>
                    )}
                  </div>
                </div>

                {/* Details Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="bg-[#0a0a0f] rounded-xl border border-[#1e1e2e] p-4">
                    <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">
                      {detail.all_violation_types && detail.all_violation_types.length > 1 ? 'Violations' : 'Type'}
                    </p>
                    {detail.all_violation_types && detail.all_violation_types.length > 1 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {detail.all_violation_types.map((t) => (
                          <span
                            key={t}
                            className="text-[11px] font-semibold capitalize px-2 py-0.5 rounded bg-orange-500/10 text-orange-400 border border-orange-500/20"
                          >
                            {t.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="font-semibold capitalize text-sm">{detail.violation_type.replace(/_/g, ' ')}</p>
                    )}
                  </div>
                  <div className="bg-[#0a0a0f] rounded-xl border border-[#1e1e2e] p-4">
                    <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">Severity</p>
                    <SeverityBadge severity={detail.severity} />
                  </div>
                  <div className="bg-[#0a0a0f] rounded-xl border border-[#1e1e2e] p-4">
                    <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">Confidence</p>
                    <ConfidenceBadge value={detail.confidence} />
                  </div>
                  <div className="bg-[#0a0a0f] rounded-xl border border-[#1e1e2e] p-4 col-span-2">
                    <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">License Plate (OCR)</p>
                    {detail.plate_number ? (
                      <p className="font-mono text-lg font-semibold tracking-wider text-emerald-400">{detail.plate_number}</p>
                    ) : (
                      <p className="text-sm text-gray-500">Plate not legible in source frame</p>
                    )}
                  </div>
                  <div className="bg-[#0a0a0f] rounded-xl border border-[#1e1e2e] p-4">
                    <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">Vehicle</p>
                    <p className="text-sm capitalize text-gray-300">{detail.vehicle_category ?? '—'}</p>
                  </div>
                  <div className="bg-[#0a0a0f] rounded-xl border border-[#1e1e2e] p-4">
                    <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">Status</p>
                    <p className="text-sm capitalize text-gray-300">{detail.status}</p>
                  </div>
                  <div className="bg-[#0a0a0f] rounded-xl border border-[#1e1e2e] p-4 col-span-2">
                    <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">Detected At</p>
                    <p className="text-sm text-gray-300">
                      {detail.detected_at ? new Date(detail.detected_at).toLocaleString() : '—'}
                    </p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-3 pt-2 border-t border-[#1e1e2e]">
                  <button
                    onClick={() => {
                      updateStatus.mutate({ id: detail.id, status: 'confirmed' });
                    }}
                    disabled={detail.status === 'confirmed' || updateStatus.isPending}
                    className="flex-1 flex items-center justify-center gap-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-semibold py-2.5 rounded-xl hover:bg-emerald-500/20 transition-colors disabled:opacity-30"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    Confirm Violation
                  </button>
                  <button
                    onClick={() => {
                      updateStatus.mutate({ id: detail.id, status: 'dismissed' });
                    }}
                    disabled={detail.status === 'dismissed' || updateStatus.isPending}
                    className="flex-1 flex items-center justify-center gap-2 bg-red-500/10 border border-red-500/20 text-red-400 font-semibold py-2.5 rounded-xl hover:bg-red-500/20 transition-colors disabled:opacity-30"
                  >
                    <XCircle className="w-4 h-4" />
                    Dismiss
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
