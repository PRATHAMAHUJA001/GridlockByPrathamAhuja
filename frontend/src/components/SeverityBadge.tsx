const STYLES: Record<string, string> = {
  low: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
  medium: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  high: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  critical: 'bg-red-500/10 text-red-400 border-red-500/20',
};

export default function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      className={`text-[10px] font-bold tracking-wider px-2.5 py-1 rounded border uppercase ${STYLES[severity] ?? 'bg-gray-500/10 text-gray-400 border-gray-500/20'}`}
    >
      {severity}
    </span>
  );
}
