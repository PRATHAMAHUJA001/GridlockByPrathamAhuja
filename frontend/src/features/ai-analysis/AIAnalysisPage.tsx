import { useState, useCallback, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Upload,
  Loader2,
  BarChart3,
  Camera,
  Eye,
  Target,
  Gauge,
  Database,
  CheckCircle2,
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { EvaluationResponse, MetricSet, StoredImageSummary } from '../../types';
import ConfidenceBadge from '../../components/ConfidenceBadge';
import SeverityBadge from '../../components/SeverityBadge';
import api from '../../lib/api-client';

const VIOLATION_TYPES = [
  'helmet',
  'seatbelt',
  'triple_riding',
  'wrong_side',
  'stop_line',
  'red_light',
  'illegal_parking',
] as const;

const tooltipStyle = {
  background: '#12121a',
  border: '1px solid #1e1e2e',
  borderRadius: 10,
  fontSize: 12,
  boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
};

function MetricCard({ label, metrics }: { label: string; metrics: MetricSet }) {
  const colorFor = (v: number) => (v >= 0.8 ? '#10b981' : v >= 0.5 ? '#f59e0b' : '#ef4444');
  const rows: [string, number][] = [
    ['Accuracy', metrics.accuracy],
    ['Precision', metrics.precision],
    ['Recall', metrics.recall],
    ['F1 Score', metrics.f1_score],
    ['mAP', metrics.mean_average_precision ?? 0],
  ];
  return (
    <div className="rounded-xl border border-[#1e1e2e] p-5 space-y-4" style={{ background: 'rgba(18,18,26,0.8)' }}>
      <h4 className="font-semibold text-sm tracking-wide text-gray-300">{label}</h4>
      <div className="grid grid-cols-5 gap-3">
        {rows.map(([name, val]) => (
          <div key={name} className="text-center">
            <p className="text-2xl font-bold" style={{ color: colorFor(val) }}>{(val * 100).toFixed(1)}%</p>
            <p className="text-[11px] text-gray-500 mt-1 tracking-wide">{name}</p>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-4 pt-3 border-t border-[#1e1e2e]">
        <div className="text-center">
          <p className="text-xl font-bold text-emerald-400">{metrics.true_positives}</p>
          <p className="text-xs text-gray-600">True Pos</p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-red-400">{metrics.false_positives}</p>
          <p className="text-xs text-gray-600">False Pos</p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-amber-400">{metrics.false_negatives}</p>
          <p className="text-xs text-gray-600">False Neg</p>
        </div>
      </div>
    </div>
  );
}

export default function AIAnalysisPage() {
  const [mode, setMode] = useState<'upload' | 'database'>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [storedImages, setStoredImages] = useState<StoredImageSummary[]>([]);
  const [selectedImage, setSelectedImage] = useState<StoredImageSummary | null>(null);
  const [groundTruth, setGroundTruth] = useState<Set<string>>(new Set());
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [evalResult, setEvalResult] = useState<EvaluationResponse | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // Load stored DB images when switching to database mode
  useEffect(() => {
    if (mode !== 'database') return;
    api
      .get<StoredImageSummary[]>('/evaluate/images?limit=30')
      .then((r) => setStoredImages(r.data))
      .catch(() => setStoredImages([]));
  }, [mode]);

  const toggleGroundTruth = (type: string) => {
    setGroundTruth((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  const onDrop = useCallback((files: File[]) => {
    if (files[0]) {
      setFile(files[0]);
      setPreview(URL.createObjectURL(files[0]));
      setEvalResult(null);
      setError(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.bmp'] },
    maxFiles: 1,
  });

  const canRun =
    groundTruth.size > 0 && (mode === 'upload' ? !!file : !!selectedImage) && !isEvaluating;

  const runEvaluation = useCallback(async () => {
    setIsEvaluating(true);
    setError(null);
    setEvalResult(null);
    try {
      let data: EvaluationResponse;
      if (mode === 'upload') {
        if (!file) return;
        const fd = new FormData();
        fd.append('file', file);
        fd.append('ground_truth', JSON.stringify(Array.from(groundTruth)));
        ({ data } = await api.post<EvaluationResponse>('/evaluate', fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        }));
      } else {
        if (!selectedImage) return;
        const fd = new FormData();
        fd.append('ground_truth', JSON.stringify(Array.from(groundTruth)));
        ({ data } = await api.post<EvaluationResponse>(`/evaluate/images/${selectedImage.id}`, fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        }));
      }
      setEvalResult(data);
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? err?.message ?? 'Evaluation failed');
    } finally {
      setIsEvaluating(false);
    }
  }, [mode, file, selectedImage, groundTruth]);

  const chartData = evalResult
    ? [
        { metric: 'Accuracy', value: +(evalResult.cv_metrics.accuracy * 100).toFixed(1) },
        { metric: 'Precision', value: +(evalResult.cv_metrics.precision * 100).toFixed(1) },
        { metric: 'Recall', value: +(evalResult.cv_metrics.recall * 100).toFixed(1) },
        { metric: 'F1', value: +(evalResult.cv_metrics.f1_score * 100).toFixed(1) },
        { metric: 'mAP', value: +((evalResult.cv_metrics.mean_average_precision ?? 0) * 100).toFixed(1) },
      ]
    : [];

  const evidenceUrl = evalResult?.cv_results?.evidence_url ?? '';
  const previewSrc = mode === 'upload' ? preview : selectedImage?.image_url ?? null;

  return (
    <div className="min-h-screen bg-[#0a0a0f] p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600">
          <BarChart3 className="w-5 h-5 text-white" />
        </div>
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Performance Evaluation</h2>
          <p className="text-xs text-gray-500 tracking-wide">
            Accuracy · Precision · Recall · F1 · mAP for the CV detection pipeline
          </p>
        </div>
      </div>

      {/* Source mode toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => { setMode('upload'); setEvalResult(null); }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
            mode === 'upload'
              ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'
              : 'border-[#1e1e2e] text-gray-500 hover:text-gray-300'
          }`}
        >
          <Upload className="w-4 h-4" /> Upload Image
        </button>
        <button
          onClick={() => { setMode('database'); setEvalResult(null); }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
            mode === 'database'
              ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'
              : 'border-[#1e1e2e] text-gray-500 hover:text-gray-300'
          }`}
        >
          <Database className="w-4 h-4" /> From Database
        </button>
      </div>

      {/* Section A: Image source + Ground Truth */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Image picker */}
        <div>
          {mode === 'upload' ? (
            <>
              <div
                {...getRootProps()}
                className={`relative rounded-xl p-12 text-center cursor-pointer transition-all duration-300 border-2 border-dashed ${
                  isDragActive ? 'border-cyan-500 bg-cyan-500/5' : 'border-[#1e1e2e] hover:border-[#2a2a3e]'
                }`}
                style={{ background: isDragActive ? undefined : 'rgba(18,18,26,0.5)' }}
              >
                <input {...getInputProps()} />
                <div className="p-4 rounded-2xl bg-gradient-to-br from-cyan-500/10 to-blue-500/5 border border-[#1e1e2e] w-fit mx-auto mb-4">
                  <Upload className="w-10 h-10 text-gray-500" />
                </div>
                <p className="text-gray-400 text-sm">
                  {isDragActive ? 'Drop image here...' : 'Drag & drop a traffic image, or click to select'}
                </p>
                <p className="text-xs text-gray-600 mt-2">Supports JPG, PNG, BMP</p>
              </div>
              {preview && (
                <img src={preview} alt="Preview" className="mt-4 rounded-xl w-full max-h-64 object-contain border border-[#1e1e2e]" style={{ background: 'rgba(18,18,26,0.8)' }} />
              )}
            </>
          ) : (
            <div className="rounded-xl border border-[#1e1e2e] p-4 space-y-3" style={{ background: 'rgba(18,18,26,0.5)' }}>
              <p className="text-xs text-gray-500">Select a previously processed image from the database:</p>
              {storedImages.length === 0 ? (
                <p className="text-sm text-gray-600 py-8 text-center">No stored images yet — run a detection first.</p>
              ) : (
                <div className="grid grid-cols-3 gap-2 max-h-80 overflow-auto">
                  {storedImages.map((img) => (
                    <button
                      key={img.id}
                      onClick={() => { setSelectedImage(img); setEvalResult(null); }}
                      className={`relative rounded-lg overflow-hidden border-2 transition-all ${
                        selectedImage?.id === img.id ? 'border-cyan-500' : 'border-transparent hover:border-[#2a2a3e]'
                      }`}
                    >
                      <img src={img.image_url} alt="stored" className="w-full h-20 object-cover" />
                      {selectedImage?.id === img.id && (
                        <div className="absolute top-1 right-1 bg-cyan-500 rounded-full p-0.5">
                          <CheckCircle2 className="w-3 h-3 text-white" />
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              )}
              {selectedImage && (
                <img src={selectedImage.image_url} alt="Selected" className="rounded-lg w-full max-h-56 object-contain border border-[#1e1e2e]" />
              )}
            </div>
          )}
        </div>

        {/* Ground truth */}
        <div className="rounded-xl border border-[#1e1e2e] p-5 space-y-4" style={{ background: 'rgba(18,18,26,0.8)' }}>
          <h3 className="font-semibold text-sm tracking-wide text-gray-300 flex items-center gap-2">
            <Target className="w-4 h-4 text-cyan-400" />
            Ground Truth
          </h3>
          <p className="text-xs text-gray-600">Select the violations actually present in the image:</p>
          <div className="grid grid-cols-2 gap-2">
            {VIOLATION_TYPES.map((type) => (
              <label
                key={type}
                className={`flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer text-sm transition-all duration-200 border ${
                  groundTruth.has(type)
                    ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'
                    : 'border-[#1e1e2e] text-gray-500 hover:border-[#2a2a3e] hover:text-gray-400'
                }`}
                style={{ background: groundTruth.has(type) ? undefined : 'rgba(26,26,46,0.5)' }}
              >
                <input
                  type="checkbox"
                  checked={groundTruth.has(type)}
                  onChange={() => toggleGroundTruth(type)}
                  className="accent-cyan-500 w-3.5 h-3.5"
                />
                <span className="capitalize text-xs">{type.replace(/_/g, ' ')}</span>
              </label>
            ))}
          </div>
          <button
            onClick={runEvaluation}
            disabled={!canRun}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-30 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg transition-all duration-200 text-sm"
          >
            {isEvaluating ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
            Run Evaluation
          </button>
          {isEvaluating && (
            <p className="text-xs text-gray-600 text-center">
              Running detection pipeline + OCR — this can take up to ~60s on CPU.
            </p>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-800/30 p-4 text-red-300 text-sm" style={{ background: 'rgba(127,29,29,0.1)' }}>
          Error: {error}
        </div>
      )}

      {/* Results */}
      {evalResult && (
        <div ref={resultsRef}>
          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-3">
              <BarChart3 className="w-5 h-5 text-cyan-400" />
              <h3 className="text-lg font-bold tracking-tight text-white">Evaluation Metrics</h3>
            </div>
            {evalResult.inference_latency_ms != null && (
              <span className="flex items-center gap-1.5 text-xs text-gray-400 font-mono bg-[#12121a] border border-[#1e1e2e] px-3 py-1.5 rounded-lg">
                <Gauge className="w-3.5 h-3.5 text-cyan-400" />
                Inference: {(evalResult.inference_latency_ms / 1000).toFixed(1)}s
              </span>
            )}
          </div>

          <MetricCard label="CV Detection Pipeline" metrics={evalResult.cv_metrics} />

          {/* Bar chart */}
          <div className="rounded-xl border border-[#1e1e2e] p-5" style={{ background: 'rgba(18,18,26,0.8)' }}>
            <h4 className="font-semibold text-sm tracking-wide text-gray-300 mb-4">Metric Breakdown</h4>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData} barGap={8}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" vertical={false} />
                <XAxis dataKey="metric" tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={{ stroke: '#1e1e2e' }} tickLine={false} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} domain={[0, 100]} tickFormatter={(v) => `${v}%`} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: '#e5e7eb' }} formatter={(value) => [`${Number(value ?? 0)}%`]} />
                <Bar dataKey="value" fill="#06b6d4" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Ground truth vs detected */}
          <div className="rounded-xl border border-[#1e1e2e] p-5 space-y-4" style={{ background: 'rgba(18,18,26,0.8)' }}>
            <h4 className="font-semibold text-sm tracking-wide text-gray-300">Ground Truth vs Detected</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-xs text-gray-600 mb-2 uppercase tracking-wider font-medium">Ground Truth</p>
                {evalResult.ground_truth.map((v, i) => (
                  <div key={i} className="rounded-lg px-3 py-1.5 mb-1 capitalize text-gray-400 border border-[#1e1e2e]" style={{ background: 'rgba(26,26,46,0.5)' }}>
                    {v.replace(/_/g, ' ')}
                  </div>
                ))}
              </div>
              <div>
                <p className="text-xs text-gray-600 mb-2 uppercase tracking-wider font-medium">CV Detected</p>
                {evalResult.cv_detections.length === 0 && <p className="text-xs text-gray-600">None</p>}
                {evalResult.cv_detections.map((v, i) => {
                  const isTP = evalResult.ground_truth.includes(v);
                  return (
                    <div
                      key={i}
                      className={`rounded-lg px-3 py-1.5 mb-1 capitalize border ${
                        isTP ? 'border-emerald-500/20 text-emerald-300' : 'border-red-500/20 text-red-300'
                      }`}
                      style={{ background: isTP ? 'rgba(16,185,129,0.05)' : 'rgba(239,68,68,0.05)' }}
                    >
                      {v.replace(/_/g, ' ')} {isTP ? '' : '(FP)'}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Detected violations detail */}
          {evalResult.cv_results?.violations?.length > 0 && (
            <div className="rounded-xl border border-[#1e1e2e] p-5 space-y-2" style={{ background: 'rgba(18,18,26,0.8)' }}>
              <h4 className="font-semibold text-sm tracking-wide text-gray-300 mb-1">Detected Violations</h4>
              {evalResult.cv_results.violations.map((v, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg px-4 py-3 border border-[#1e1e2e]" style={{ background: 'rgba(26,26,46,0.5)' }}>
                  <div className="flex items-center gap-3">
                    <span className="font-medium capitalize text-sm text-gray-300">{v.violation_type.replace(/_/g, ' ')}</span>
                    <SeverityBadge severity={v.severity} />
                  </div>
                  <ConfidenceBadge value={v.confidence} />
                </div>
              ))}
            </div>
          )}

          {/* Evidence images */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="rounded-xl border border-[#1e1e2e] p-4" style={{ background: 'rgba(18,18,26,0.8)' }}>
              <h3 className="font-semibold text-sm tracking-wide text-gray-300 mb-3 flex items-center gap-2">
                <Camera className="w-4 h-4 text-gray-500" />
                Original
              </h3>
              {previewSrc && <img src={previewSrc} alt="Original" className="rounded-lg w-full" />}
            </div>
            <div className="rounded-xl border border-[#1e1e2e] p-4" style={{ background: 'rgba(18,18,26,0.8)' }}>
              <h3 className="font-semibold text-sm tracking-wide text-gray-300 mb-3 flex items-center gap-2">
                <Eye className="w-4 h-4 text-cyan-400" />
                Annotated Evidence
              </h3>
              {evidenceUrl && <img src={evidenceUrl} alt="Evidence" className="rounded-lg w-full" />}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
