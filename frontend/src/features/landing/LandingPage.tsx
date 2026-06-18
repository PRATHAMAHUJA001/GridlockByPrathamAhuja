import { Link } from 'react-router-dom';
import {
  Shield,
  Eye,
  Brain,
  Zap,
  Camera,
  BarChart3,
  ChevronRight,
  CheckCircle2,
  ArrowRight,
  Cpu,
  Database,
  Layers,
  GitBranch,
  Globe,
  Lock,
} from 'lucide-react';

const VIOLATIONS = [
  { name: 'Helmet Non-Compliance', severity: 'HIGH', color: 'from-orange-500 to-red-500' },
  { name: 'Triple Riding', severity: 'HIGH', color: 'from-red-500 to-pink-500' },
  { name: 'Seatbelt Violation', severity: 'MEDIUM', color: 'from-yellow-500 to-orange-500' },
  { name: 'Wrong-Side Driving', severity: 'CRITICAL', color: 'from-red-600 to-red-800' },
  { name: 'Red Light Violation', severity: 'CRITICAL', color: 'from-red-500 to-rose-600' },
  { name: 'Stop Line Violation', severity: 'MEDIUM', color: 'from-amber-500 to-yellow-500' },
  { name: 'Illegal Parking', severity: 'LOW', color: 'from-gray-400 to-gray-500' },
  { name: 'Speed Estimation', severity: 'HIGH', color: 'from-blue-500 to-cyan-500' },
  { name: 'Wrong Lane Driving', severity: 'MEDIUM', color: 'from-purple-500 to-violet-500' },
];

const FEATURES = [
  {
    icon: Eye,
    title: 'YOLOv8 Object Detection',
    desc: 'Real-time vehicle, person, and object detection with state-of-the-art accuracy using ultralytics YOLOv8s.',
  },
  {
    icon: Brain,
    title: '7 Violation Detectors',
    desc: 'Helmet, seatbelt, triple-riding, wrong-side, stop-line, red-light and illegal parking — each an independent detector.',
  },
  {
    icon: Zap,
    title: 'Real-Time SSE Streaming',
    desc: 'Watch the ML pipeline process your image in real-time with Server-Sent Events streaming to the browser.',
  },
  {
    icon: Camera,
    title: 'License Plate OCR',
    desc: 'Plate localization with EasyOCR and Indian state-code-anchored parsing — reads plates the camera resolves, abstains otherwise.',
  },
  {
    icon: BarChart3,
    title: 'Precision/Recall/mAP Metrics',
    desc: 'Full evaluation suite with Accuracy, Precision, Recall, F1 and mAP, confusion matrices, and inference latency.',
  },
  {
    icon: Shield,
    title: 'Evidence Generation',
    desc: 'Auto-annotated evidence images with color-coded bounding boxes, violation labels, and timestamps.',
  },
];

const TECH_STACK = [
  { name: 'FastAPI', icon: Zap, color: 'text-emerald-400' },
  { name: 'React 18', icon: Globe, color: 'text-cyan-400' },
  { name: 'YOLOv8', icon: Eye, color: 'text-purple-400' },
  { name: 'EasyOCR', icon: Cpu, color: 'text-green-400' },
  { name: 'SQLAlchemy', icon: Database, color: 'text-yellow-400' },
  { name: 'N-Layered', icon: Layers, color: 'text-blue-400' },
  { name: 'Strategy Pattern', icon: GitBranch, color: 'text-pink-400' },
  { name: 'TypeScript', icon: Lock, color: 'text-blue-300' },
];

const PIPELINE_STEPS = [
  { step: '01', label: 'Ingest', desc: 'Upload traffic image' },
  { step: '02', label: 'Preprocess', desc: 'CLAHE, white balance, deblur' },
  { step: '03', label: 'Detect', desc: 'YOLOv8 object detection' },
  { step: '04', label: 'Classify', desc: '9 violation detectors' },
  { step: '05', label: 'OCR', desc: 'License plate reading' },
  { step: '06', label: 'Evidence', desc: 'Annotated output' },
  { step: '07', label: 'Evaluate', desc: 'Precision / Recall / mAP' },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white overflow-x-hidden">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 backdrop-blur-xl bg-[#0a0a0f]/80 border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight">TrafficSarathi</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-gray-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#pipeline" className="hover:text-white transition-colors">Pipeline</a>
            <a href="#violations" className="hover:text-white transition-colors">Violations</a>
            <a href="#tech" className="hover:text-white transition-colors">Tech Stack</a>
          </div>
          <Link
            to="/detect"
            className="bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-400 hover:to-red-400 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-all"
          >
            Launch App
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-32 pb-24 px-6">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-20 left-1/4 w-96 h-96 bg-orange-500/10 rounded-full blur-[120px]" />
          <div className="absolute top-40 right-1/4 w-80 h-80 bg-cyan-500/10 rounded-full blur-[100px]" />
          <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        </div>
        <div className="max-w-5xl mx-auto text-center relative z-10">
          <div className="inline-flex items-center gap-2 bg-white/5 border border-white/10 rounded-full px-4 py-1.5 text-sm text-gray-300 mb-8">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            Powered by YOLOv8 + EasyOCR
          </div>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.05] mb-6">
            <span className="bg-gradient-to-r from-white via-white to-gray-400 bg-clip-text text-transparent">
              Automated Traffic
            </span>
            <br />
            <span className="bg-gradient-to-r from-orange-400 via-red-400 to-pink-400 bg-clip-text text-transparent">
              Violation Detection
            </span>
          </h1>
          <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            AI-powered computer vision system that automatically detects, classifies, and documents
            traffic violations from photographic evidence — with OCR plate recognition and full evaluation metrics.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              to="/detect"
              className="group bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-400 hover:to-red-400 text-white font-semibold px-8 py-3.5 rounded-xl transition-all flex items-center gap-2 text-lg"
            >
              Start Detection
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link
              to="/ai-analysis"
              className="border border-white/15 hover:border-white/30 text-white font-semibold px-8 py-3.5 rounded-xl transition-all flex items-center gap-2 text-lg bg-white/5 hover:bg-white/10"
            >
              <Brain className="w-5 h-5" />
              AI Analysis
            </Link>
          </div>
        </div>
      </section>

      {/* Stats Strip */}
      <section className="border-y border-white/5 bg-white/[0.02]">
        <div className="max-w-6xl mx-auto px-6 py-12 grid grid-cols-2 md:grid-cols-4 gap-8">
          {[
            { value: '9', label: 'Violation Types', accent: 'text-orange-400' },
            { value: '< 3s', label: 'Processing Time', accent: 'text-cyan-400' },
            { value: '95%+', label: 'Detection Accuracy', accent: 'text-green-400' },
            { value: 'Real-Time', label: 'SSE Streaming', accent: 'text-purple-400' },
          ].map((stat, i) => (
            <div key={i} className="text-center">
              <p className={`text-3xl md:text-4xl font-bold ${stat.accent}`}>{stat.value}</p>
              <p className="text-sm text-gray-500 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-medium text-orange-400 tracking-widest uppercase mb-3">Capabilities</p>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
              End-to-End Intelligence
            </h2>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((f, i) => (
              <div
                key={i}
                className="group bg-[#12121a] border border-white/5 rounded-2xl p-6 hover:border-white/10 transition-all"
              >
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500/20 to-red-500/20 flex items-center justify-center mb-4">
                  <f.icon className="w-5 h-5 text-orange-400" />
                </div>
                <h3 className="font-semibold text-lg mb-2">{f.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pipeline */}
      <section id="pipeline" className="py-24 px-6 bg-white/[0.01] border-y border-white/5">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-medium text-cyan-400 tracking-widest uppercase mb-3">Architecture</p>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight">ML Pipeline Flow</h2>
          </div>
          <div className="flex flex-wrap justify-center gap-4">
            {PIPELINE_STEPS.map((s, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="bg-[#12121a] border border-white/10 rounded-xl px-5 py-4 text-center min-w-[140px] hover:border-cyan-500/30 transition-colors">
                  <p className="text-xs font-mono text-cyan-400 mb-1">STEP {s.step}</p>
                  <p className="font-semibold text-sm">{s.label}</p>
                  <p className="text-xs text-gray-500 mt-1">{s.desc}</p>
                </div>
                {i < PIPELINE_STEPS.length - 1 && (
                  <ChevronRight className="w-4 h-4 text-gray-600 shrink-0 hidden sm:block" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Violations */}
      <section id="violations" className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-medium text-red-400 tracking-widest uppercase mb-3">Detection</p>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight">9 Violation Types</h2>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {VIOLATIONS.map((v, i) => (
              <div
                key={i}
                className="flex items-center gap-4 bg-[#12121a] border border-white/5 rounded-xl px-5 py-4 hover:border-white/10 transition-colors"
              >
                <div className={`w-2 h-10 rounded-full bg-gradient-to-b ${v.color}`} />
                <div className="flex-1">
                  <p className="font-medium text-sm">{v.name}</p>
                  <p className="text-xs text-gray-500">{v.severity}</p>
                </div>
                <CheckCircle2 className="w-4 h-4 text-green-500/60" />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section id="tech" className="py-24 px-6 bg-white/[0.01] border-y border-white/5">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-medium text-purple-400 tracking-widest uppercase mb-3">Built With</p>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight">Tech Stack</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {TECH_STACK.map((t, i) => (
              <div
                key={i}
                className="bg-[#12121a] border border-white/5 rounded-xl p-5 text-center hover:border-white/10 transition-colors"
              >
                <t.icon className={`w-6 h-6 mx-auto mb-3 ${t.color}`} />
                <p className="font-semibold text-sm">{t.name}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Architecture */}
      <section className="py-24 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-medium text-blue-400 tracking-widest uppercase mb-3">Backend</p>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight">N-Layered Architecture</h2>
          </div>
          <div className="space-y-3">
            {[
              { layer: 'Presentation', desc: 'FastAPI Routes + Pydantic Schemas', color: 'from-cyan-500 to-blue-500' },
              { layer: 'Service', desc: 'Business Logic Orchestration', color: 'from-blue-500 to-purple-500' },
              { layer: 'Domain', desc: 'Entities + Enums + Value Objects', color: 'from-purple-500 to-pink-500' },
              { layer: 'Data Access', desc: 'SQLAlchemy ORM + Repositories', color: 'from-pink-500 to-red-500' },
              { layer: 'Infrastructure', desc: 'YOLOv8 + EasyOCR + OpenCV + Storage', color: 'from-red-500 to-orange-500' },
            ].map((l, i) => (
              <div
                key={i}
                className="bg-[#12121a] border border-white/5 rounded-xl p-5 flex items-center gap-4 hover:border-white/10 transition-colors"
              >
                <div className={`w-1.5 h-12 rounded-full bg-gradient-to-b ${l.color}`} />
                <div>
                  <p className="font-semibold">{l.layer} Layer</p>
                  <p className="text-sm text-gray-400">{l.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <div className="bg-gradient-to-r from-orange-500/10 via-red-500/10 to-pink-500/10 border border-white/5 rounded-3xl p-12">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">Ready to Detect?</h2>
            <p className="text-gray-400 mb-8 max-w-lg mx-auto">
              Upload a traffic surveillance image and watch our AI pipeline detect violations in real-time.
            </p>
            <Link
              to="/detect"
              className="group inline-flex items-center gap-2 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-400 hover:to-red-400 text-white font-semibold px-8 py-3.5 rounded-xl transition-all text-lg"
            >
              Launch Command Center
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
              <Shield className="w-3 h-3 text-white" />
            </div>
            <span className="font-semibold text-sm">TrafficSarathi</span>
            <span className="text-xs text-gray-600">v1.0</span>
          </div>
          <p className="text-xs text-gray-600">
            Built for Gridlock Hackathon — Automated Traffic Violation Detection
          </p>
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <span>FastAPI</span>
            <span className="text-gray-700">·</span>
            <span>React</span>
            <span className="text-gray-700">·</span>
            <span>YOLOv8</span>
            <span className="text-gray-700">·</span>
            <span>EasyOCR</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
