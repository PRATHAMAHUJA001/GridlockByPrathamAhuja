import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Upload,
  Loader2,
  AlertTriangle,
  Camera,
  Car,
  CheckCircle2,
  Circle,
  Eye,
  Zap,
  Shield,
} from 'lucide-react';
import type { DetectionResponse } from '../../types';
import ConfidenceBadge from '../../components/ConfidenceBadge';
import SeverityBadge from '../../components/SeverityBadge';

interface PipelineStep {
  id: string;
  label: string;
  message: string;
  status: 'pending' | 'active' | 'done';
  progress: number;
}

const INITIAL_STEPS: PipelineStep[] = [
  { id: 'upload', label: 'Upload & Load', message: '', status: 'pending', progress: 0 },
  { id: 'preprocess', label: 'Preprocessing', message: '', status: 'pending', progress: 0 },
  { id: 'detection', label: 'Object Detection (YOLOv8)', message: '', status: 'pending', progress: 0 },
  { id: 'classification', label: 'Violation Classification', message: '', status: 'pending', progress: 0 },
  { id: 'ocr', label: 'License Plate OCR', message: '', status: 'pending', progress: 0 },
  { id: 'evidence', label: 'Evidence Generation', message: '', status: 'pending', progress: 0 },
  { id: 'persist', label: 'Save to Database', message: '', status: 'pending', progress: 0 },
];

export default function DetectionPage() {
  const [result, setResult] = useState<DetectionResponse | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [steps, setSteps] = useState<PipelineStep[]>(INITIAL_STEPS);
  const [isProcessing, setIsProcessing] = useState(false);
  const [overallProgress, setOverallProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [processingTime, setProcessingTime] = useState<number | null>(null);
  const [platesPending, setPlatesPending] = useState(false);
  const [maxPlates, setMaxPlates] = useState(5);

  const processFile = useCallback((file: File) => {
    setPreview(URL.createObjectURL(file));
    setResult(null);
    setError(null);
    setIsProcessing(true);
    setProcessingTime(null);
    setPlatesPending(false);
    setSteps(INITIAL_STEPS.map((s) => ({ ...s })));
    setOverallProgress(0);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('max_plates', maxPlates.toString());

    fetch('/api/v1/detect/stream', { method: 'POST', body: formData })
      .then((response) => {
        if (!response.ok) throw new Error(`Server error: ${response.status}`);
        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        function processChunk(): Promise<void> {
          return reader.read().then(({ done, value }) => {
            if (done) {
              setIsProcessing(false);
              return;
            }
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            let eventType = '';

            for (const line of lines) {
              if (line.startsWith('event: ')) {
                eventType = line.slice(7).trim();
              } else if (line.startsWith('data: ')) {
                try {
                  const parsed = JSON.parse(line.slice(6));
                  if (eventType === 'step') {
                    handleStepEvent(parsed);
                  } else if (eventType === 'result') {
                    setResult(parsed as DetectionResponse);
                    setIsProcessing(false);
                    setPlatesPending(!!parsed.plates_pending);
                    if (parsed.processing_time) {
                      setProcessingTime(parsed.processing_time);
                    }
                  } else if (eventType === 'plates') {
                    // Async OCR finished — fill in plates and refresh the evidence image.
                    setResult((prev) =>
                      prev
                        ? {
                            ...prev,
                            plates: parsed.plates ?? [],
                            evidence_url: parsed.evidence_url
                              ? `${parsed.evidence_url}?t=${Date.now()}`
                              : prev.evidence_url,
                          }
                        : prev
                    );
                    setPlatesPending(false);
                  }
                } catch {
                  // partial JSON
                }
              }
            }
            return processChunk();
          });
        }

        return processChunk();
      })
      .catch((err) => {
        setError(err.message);
        setIsProcessing(false);
      });
  }, [maxPlates]);

  const handleStepEvent = (data: { step: string; message: string; progress: number }) => {
    setOverallProgress(data.progress);
    setSteps((prev) => {
      const currentIdx = prev.findIndex((s) => s.id === data.step);
      return prev.map((s, i) => {
        if (i < currentIdx && s.status !== 'done') return { ...s, status: 'done' };
        if (i === currentIdx) return { ...s, message: data.message, status: 'active' };
        return s;
      });
    });
  };

  const onDrop = useCallback(
    (files: File[]) => {
      if (files[0]) processFile(files[0]);
    },
    [processFile]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.bmp'] },
    maxFiles: 1,
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-bold tracking-tight">Live Detection</h2>
          <span className="text-[10px] font-mono bg-cyan-500/10 text-cyan-400 px-2 py-0.5 rounded tracking-wider">
            DETECTION_ENGINE_V4.2
          </span>
        </div>
        
        {/* Max Plates Config */}
        <div className="flex items-center gap-4 bg-[#12121a] border border-[#1e1e2e] rounded-xl px-4 py-2">
          <label className="text-sm text-gray-400 font-medium whitespace-nowrap">
            Max Plates OCR: <span className="text-cyan-400">{maxPlates === 100 ? 'All' : maxPlates}</span>
          </label>
          <input 
            type="range" 
            min="1" 
            max="10" 
            step="1" 
            value={maxPlates > 10 ? 10 : maxPlates}
            onChange={(e) => setMaxPlates(parseInt(e.target.value))}
            className="w-32 accent-cyan-500"
          />
          <button 
            onClick={() => setMaxPlates(100)}
            className={`text-xs px-2 py-1 rounded ${maxPlates === 100 ? 'bg-cyan-500/20 text-cyan-400' : 'bg-[#1e1e2e] text-gray-400 hover:text-gray-200'}`}
          >
            Max
          </button>
        </div>
      </div>

      {/* Upload Dropzone */}
      <div
        {...getRootProps()}
        className={`relative rounded-2xl p-1 cursor-pointer transition-all ${
          isDragActive ? 'dropzone-gradient' : ''
        }`}
      >
        <div
          className={`bg-[#12121a] border-2 border-dashed rounded-xl p-12 text-center transition-all ${
            isDragActive ? 'border-cyan-500/50 bg-cyan-500/5' : 'border-[#1e1e2e] hover:border-[#2e2e3e]'
          }`}
        >
          <input {...getInputProps()} />
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-cyan-500/10 to-blue-500/10 border border-[#1e1e2e] flex items-center justify-center mx-auto mb-4">
            <Upload className="w-6 h-6 text-cyan-400" />
          </div>
          <p className="text-gray-300 font-medium">
            {isDragActive ? 'Drop image here...' : 'Drag & drop a traffic surveillance image'}
          </p>
          <p className="text-xs text-gray-600 mt-2">Supports JPG, PNG, BMP — CCTV frames recommended</p>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Pipeline Progress */}
      {isProcessing && (
        <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold flex items-center gap-2 text-sm">
              <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
              ML Pipeline Processing
            </h3>
            <span className="text-sm text-cyan-400 font-mono">{overallProgress}%</span>
          </div>
          <div className="w-full bg-[#1e1e2e] rounded-full h-1.5 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full transition-all duration-500"
              style={{ width: `${overallProgress}%` }}
            />
          </div>
          <div className="space-y-1.5 mt-3">
            {steps.map((step, i) => (
              <div key={step.id} className="flex items-center gap-3 text-sm">
                <div className="w-5 flex justify-center">
                  {step.status === 'done' ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : step.status === 'active' ? (
                    <div className="w-2 h-2 rounded-full bg-cyan-400 glow-pulse" />
                  ) : (
                    <Circle className="w-3 h-3 text-[#2e2e3e]" />
                  )}
                </div>
                {i > 0 && <div className="absolute" />}
                <span
                  className={
                    step.status === 'done'
                      ? 'text-emerald-400'
                      : step.status === 'active'
                        ? 'text-cyan-400 font-medium'
                        : 'text-gray-600'
                  }
                >
                  {step.label}
                </span>
                {step.message && step.status !== 'pending' && (
                  <span className="text-gray-600 text-xs ml-auto font-mono">{step.message}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {result && (
        <div className="space-y-5">
          {/* Stat Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { icon: Camera, value: result.objects.length, label: 'Objects Detected', color: 'from-cyan-500 to-blue-500', textColor: 'text-cyan-400' },
              { icon: AlertTriangle, value: result.total_violations, label: 'Violations Found', color: 'from-red-500 to-orange-500', textColor: 'text-red-400' },
              { icon: Car, value: result.plates.length, label: 'Plates Read', color: 'from-amber-500 to-yellow-500', textColor: 'text-amber-400' },
              { icon: Zap, value: processingTime ? `${processingTime}s` : '—', label: 'Processing Time', color: 'from-emerald-500 to-green-500', textColor: 'text-emerald-400' },
            ].map((card, i) => (
              <div key={i} className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-4 flex items-center gap-3">
                <div className={`w-2 h-10 rounded-full bg-gradient-to-b ${card.color}`} />
                <div>
                  <p className={`text-2xl font-bold ${card.textColor}`}>{card.value}</p>
                  <p className="text-[10px] text-gray-600 uppercase tracking-wider">{card.label}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Evidence Images */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-4 space-y-3">
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider flex items-center gap-2">
                <Camera className="w-3.5 h-3.5" />
                Annotated Source
              </h3>
              {preview && <img src={preview} alt="Original" className="rounded-lg w-full" />}
            </div>
            <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-medium text-cyan-400 uppercase tracking-wider flex items-center gap-2">
                  <Eye className="w-3.5 h-3.5" />
                  AI Annotated Evidence
                </h3>
                <span className="text-[10px] font-mono text-gray-600">DETECTION_ENGINE_V4.2</span>
              </div>
              <div className="relative">
                <img src={result.evidence_url} alt="Evidence" className="rounded-lg w-full" />
                <div className="absolute top-3 left-3 flex flex-col gap-1.5">
                  {result.total_violations > 0 && (
                    <span className="bg-red-500 text-white text-[10px] font-bold px-2 py-0.5 rounded tracking-wider">
                      VIOLATION DETECTED
                    </span>
                  )}
                  {result.plates.length > 0 && (
                    <span className="bg-emerald-500 text-white text-[10px] font-bold px-2 py-0.5 rounded tracking-wider">
                      PLATE CONFIRMED
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Violations */}
          {result.violations.length > 0 && (
            <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-5 space-y-3">
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider flex items-center gap-2">
                <Shield className="w-3.5 h-3.5 text-red-400" />
                Violations Detected
              </h3>
              <div className="space-y-2">
                {result.violations.map((v, i) => (
                  <div key={i} className="flex items-center justify-between bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-4 py-3">
                    <div className="flex items-center gap-3">
                      <span className="font-medium capitalize text-sm">{v.violation_type.replace(/_/g, ' ')}</span>
                      <SeverityBadge severity={v.severity} />
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-xs text-gray-600 capitalize">{v.vehicle_category}</span>
                      <ConfidenceBadge value={v.confidence} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Plates */}
          {(result.plates.length > 0 || platesPending) && (
            <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-5 space-y-3">
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider flex items-center gap-2">
                License Plates
                {platesPending && (
                  <span className="flex items-center gap-1.5 text-cyan-400 normal-case tracking-normal">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Reading plates (OCR)…
                  </span>
                )}
              </h3>
              {platesPending && result.plates.length === 0 ? (
                <p className="text-xs text-gray-600">
                  Violations are ready above — license-plate OCR runs in the background and will
                  appear here shortly.
                </p>
              ) : (
                <div className="space-y-2">
                  {result.plates.map((p, i) => (
                    <div key={i} className="flex items-center justify-between bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-4 py-3">
                      <span className="font-mono text-lg font-semibold tracking-wider">{p.text}</span>
                      <ConfidenceBadge value={p.confidence} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
